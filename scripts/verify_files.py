#!/usr/bin/env python3
"""Read-only checks for a paper, a publisher's SI list, or two Word copies."""

import argparse
from collections import defaultdict
import hashlib
from itertools import islice
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unicodedata
from urllib.parse import unquote
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile
from zlib import error as ZlibError


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOI = re.compile(r"10\.\d{4,9}/[^\s<>\"“”]+", re.I)
ISSUES = (ValueError, OSError, RuntimeError, BadZipFile, ZlibError, ET.ParseError, subprocess.TimeoutExpired)


def title_key(value):
    return "".join(c for c in unicodedata.normalize("NFKC", value).casefold() if c.isalnum())


def doi_key(value):
    token = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I)
    token = unquote(token).casefold().rstrip(".,;:。，；")
    for opening, closing in (("(", ")"), ("[", "]")):
        while token.endswith(closing) and token.count(closing) > token.count(opening):
            token = token[:-1]
    return token


def require_file(path):
    if path.is_symlink() or not path.is_file() or not path.stat().st_size:
        raise ValueError(f"需要可读取的非空实体文件：{path.name}")


def pdf_pages(path):
    with path.open("rb") as stream:
        if b"%PDF-" not in stream.read(1024):
            raise ValueError("文件没有 PDF 文件头")
    command = os.environ.get("PDFTOTEXT") or shutil.which("pdftotext")
    if command:
        result = subprocess.run([command, "-enc", "UTF-8", str(path.resolve()), "-"],
                                capture_output=True, timeout=180)
        if result.returncode:
            raise ValueError("pdftotext 无法读取该 PDF，请打开文件复核")
        pages = result.stdout.decode("utf-8").split("\f")
        if pages and not pages[-1].strip():
            pages.pop()
        return pages
    try:
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError
    except ImportError:
        raise ValueError("需要 pdftotext 或带 pypdf 的 Python") from None
    try:
        return [page.extract_text() or "" for page in PdfReader(path).pages]
    except PyPdfError as exc:
        raise ValueError("pypdf 无法读取该 PDF，请打开文件复核") from exc


def check_paper(args):
    require_file(args.file)
    pages = pdf_pages(args.file)
    if not pages:
        raise ValueError("PDF 无可读页")
    front = re.split(r"(?im)^\s*(?:references|bibliography|参考文献)\s*$", pages[0], maxsplit=1)[0]
    if not title_key(args.title) or title_key(args.title) not in title_key(front):
        raise ValueError("首页未匹配目标题名")
    expected = doi_key(args.doi)
    identifiers = {doi_key(m) for m in DOI.findall(front.replace("\u00ad", ""))}
    if not DOI.fullmatch(expected) or expected not in identifiers:
        raise ValueError("首页未匹配目标 DOI")
    labels = {line.strip().casefold() for line in front.splitlines() if line.strip()}
    if labels & {"supporting information", "supplementary material", "supplementary materials",
                 "supplementary information", "abstract only", "补充材料", "仅摘要"}:
        raise ValueError("首页有补充材料或仅摘要标记，请核对正文版本")
    if len(pages) < 2 or not any(title_key(page) for page in pages[1:]):
        raise ValueError("题名和 DOI 已匹配，需人工核对单页正文或后续扫描页")
    print(f"首页题名与 DOI 匹配，共 {len(pages)} 页。请抽查正文中间页和末页。")


def check_zip(archive):
    if len(archive.namelist()) != len(set(archive.namelist())):
        raise ValueError("压缩包存在重名部件")
    bad = archive.testzip()
    if bad:
        raise ValueError(f"压缩包校验失败：{bad}")


def word_front(archive):
    check_zip(archive)
    if not {"[Content_Types].xml", "word/document.xml"}.issubset(archive.namelist()):
        raise ValueError("缺少 DOCX 文档部件")
    root = ET.fromstring(archive.read("word/document.xml"))
    if root.tag != W + "document":
        raise ValueError("Word 文档结构无效")
    paragraphs = ("".join(n.text or "" for n in p.iter(W + "t")) for p in root.iter(W + "p"))
    return " ".join(islice((p for p in paragraphs if p.strip()), 15))


def check_video(path):
    size = path.stat().st_size
    tags = set()
    video_track = False
    with path.open("rb") as stream:
        while stream.tell() < size:
            start = stream.tell()
            header = stream.read(8)
            if len(header) != 8:
                raise ValueError("MP4 末尾不完整")
            count, tag = struct.unpack(">I4s", header)
            if count == 1:
                extended = stream.read(8)
                if len(extended) != 8:
                    raise ValueError("MP4 扩展长度缺失")
                count = struct.unpack(">Q", extended)[0]
            end = start + count if count else size
            if not stream.tell() <= end <= size:
                raise ValueError("MP4 声明的区块长度与实际文件不符")
            tags.add(tag)
            if tag == b"moov":
                video_track = bool(re.search(rb"hdlr.{8}vide", stream.read(end - stream.tell()), re.S))
            stream.seek(end)
    if not {b"ftyp", b"moov", b"mdat"} <= tags or not video_track:
        raise ValueError("MP4 缺少视频轨道或媒体数据")
    with tempfile.TemporaryDirectory() as tmp:
        ffmpeg = shutil.which("ffmpeg")
        sample = Path(tmp) / "sample.m4v"
        if ffmpeg:
            command = [ffmpeg, "-nostdin", "-v", "error", "-xerror", "-i", str(path.resolve()),
                       "-map", "0:v:0", "-frames:v", "1", "-f", "framemd5", "-"]
        elif shutil.which("avconvert"):
            command = ["avconvert", "--source", str(path.resolve()), "--output", str(sample),
                       "--preset", "Preset640x480", "--duration", "0.5"]
        else:
            raise ValueError("视频封装可读，仍需 FFmpeg、avconvert 或播放器确认解码")
        run = subprocess.run(command, capture_output=True, timeout=120)
        decoded = (re.search(rb"(?m)^\s*\d+\s*,", run.stdout) if ffmpeg
                   else sample.is_file() and sample.stat().st_size > 0)
        if run.returncode or not decoded:
            raise ValueError("视频抽样解码失败")
    return "MP4 封装完整，已抽样解码"


def check_si_file(path, title):
    require_file(path)
    ext = path.suffix.casefold()
    if ext == ".mp4":
        return check_video(path)
    if ext == ".docx":
        with ZipFile(path) as archive:
            front = word_front(archive)
    elif ext == ".pdf":
        front = "\n".join(pdf_pages(path)[:2])
    elif ext == ".zip":
        with ZipFile(path) as archive:
            check_zip(archive)
        raise ValueError("ZIP 可读，需按出版社清单检查包内材料")
    else:
        raise ValueError(f"请用相应阅读器复核 {ext or '无扩展名'} 文件")
    if not title_key(front) or (title and title_key(title) not in title_key(front)):
        raise ValueError("文档开头缺少可读文字或未匹配目标题名，请核对作者与附件内容")
    return f"{ext[1:].upper()} 可读" + ("，已匹配论文题名" if title else "")


def file_key(name):
    return unicodedata.normalize("NFC", name).casefold()


def expected_files(manifest):
    expected = {}
    for line in manifest.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split("\t")
        name = fields[0].strip()
        if not name or name in {".", ".."} or "/" in name or "\\" in name or len(fields) > 2:
            raise ValueError(f"清单行无效：{line}")
        if file_key(name) in expected:
            raise ValueError(f"清单中重复的文件名：{name}")
        size = int(fields[1].strip()) if len(fields) == 2 and fields[1].strip() else None
        if size is not None and size <= 0:
            raise ValueError(f"精确字节数应为正整数：{name}")
        expected[file_key(name)] = (name, size)
    if not expected:
        raise ValueError("出版社清单为空")
    return expected


def check_si(args):
    expected = expected_files(args.expected)
    local = defaultdict(list)
    for path in args.directory.iterdir():
        local[file_key(path.name)].append(path)
    passed = 0
    for key, (name, size) in expected.items():
        try:
            matches = local.get(key, [])
            if not matches:
                raise ValueError("缺件")
            if len(matches) != 1:
                raise ValueError("目录中有多个同名候选")
            path = matches[0]
            if size is not None and path.stat().st_size != size:
                raise ValueError("与清单中的精确字节数不符")
            detail = check_si_file(path, args.title)
            print(f"通过  {name}  {detail}")
            passed += 1
        except ISSUES as exc:
            print(f"待复核  {name}  {exc}")
    print(f"已通过本地检查 {passed}/{len(expected)} 项")
    if passed != len(expected):
        raise ValueError("仍有缺件或待复核的附件")


def word_parts(path):
    with ZipFile(path) as archive:
        word_front(archive)
        return {item.filename: hashlib.sha256(archive.read(item)).digest()
                for item in archive.infolist() if not item.is_dir()}


def compare_word(args):
    a, b = word_parts(args.original), word_parts(args.response)
    changed = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
    content = [k for k in changed if not k.startswith("docProps/")]
    if content:
        raise ValueError("DOCX 内容部件存在差异：" + "、".join(content))
    print("DOCX 内容部件一致。" + ("属性差异：" + "、".join(changed) if changed else "全部部件一致。"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    paper = sub.add_parser("paper", help="核对正文首页题名、DOI 和页数")
    paper.add_argument("file", type=Path)
    paper.add_argument("--doi", required=True)
    paper.add_argument("--title", required=True)
    paper.set_defaults(action=check_paper)
    si = sub.add_parser("si", help="逐项核验出版社清单中的补充材料")
    si.add_argument("directory", type=Path)
    si.add_argument("--expected", type=Path, required=True, help="UTF-8 文件名清单，可附 TSV 精确字节数")
    si.add_argument("--title", help="匹配可提取文本的补充文档题名")
    si.set_defaults(action=check_si)
    compare = sub.add_parser("compare-docx", help="比对两份 DOCX 的内容部件")
    compare.add_argument("original", type=Path)
    compare.add_argument("response", type=Path)
    compare.set_defaults(action=compare_word)
    args = parser.parse_args()
    try:
        args.action(args)
    except ISSUES as exc:
        print(f"需复核  {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
