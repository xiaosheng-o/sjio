# 本地核验与离线复现

在项目根目录执行。本例使用 DOI `10.1002/adma.75831`。使用 Python 3.9 或更新版本。PDF 检查使用 Poppler 的 `pdftotext` 或 Python 包 `pypdf`，可用 `PDFTOTEXT` 指定可执行文件，也可选用 Codex 桌面工作区依赖返回的 Python。视频检查使用 FFmpeg，macOS 也可用系统的 `avconvert`。

## 核验本次应助

将 `incoming_pdf` 设为正文帖这次实际交来的 PDF，将 `incoming_si` 设为补充材料帖这次实际交来的附件所在目录。如果收到了压缩包或网盘说明，先取回并展开里面的文件。下面两条命令分别针对两个帖子。

```sh
skill_dir="${CODEX_HOME:-$HOME/.codex}/skills/ablesci-assist"
title='A Mesohydrous Metallic Gel for Imperceptible Electrophysiology'
expected="$skill_dir/references/adma75831-si.txt"
python3 "$skill_dir/scripts/verify_files.py" paper "${incoming_pdf:?请先指定本次收件的正文路径}" \
  --title "$title" --doi '10.1002/adma.75831'
python3 "$skill_dir/scripts/verify_files.py" si "${incoming_si:?请先指定本次收件的补充材料目录}" \
  --expected "$expected" --title "$title"
```

如果这次返回 6/7，提示缺少 `adma75831-sup-0005-VideoS4.mp4`，则求全部补充材料的帖子继续待确认。即使下面的归档检查返回 7/7，也须等该帖补交 S4。正文帖可按自己的结果采纳。

## 复核归档或离线回放

本次收件通过后，归档到项目并运行以下命令。若只复现已办结的旧案例，直接在现有项目运行这一段即可，它会只读检查已保存的文件。

```sh
skill_dir="${CODEX_HOME:-$HOME/.codex}/skills/ablesci-assist"
title='A Mesohydrous Metallic Gel for Imperceptible Electrophysiology'
python3 "$skill_dir/scripts/verify_files.py" paper "$PWD/$title.pdf" \
  --title "$title" --doi '10.1002/adma.75831'
python3 "$skill_dir/scripts/verify_files.py" si "$PWD/补充材料" \
  --expected "$skill_dir/references/adma75831-si.txt" --title "$title"
```

本例正文共 14 页。出版社列出 1 份 DOCX 和 6 个 MP4，共 7 项。网盘说明和下载回执另计。样例清单取自这篇论文的 Supporting Information。[出版社论文页](https://advanced.onlinelibrary.wiley.com/doi/10.1002/adma.75831)

其他论文要从其出版社补充材料表建立独立清单。UTF-8 文本每行写一个官方文件名，可在制表符后附上已知的精确字节数。网页只给出约数时留空。将独立清单传给 `--expected`。从本地下载结果反推清单会漏掉尚未下载的附件。归档时使用清单里的文件名，允许大小写差异。不同论文的文件名冲突时，为它们分别使用独立子目录。

两份 Word 文档字节数或 SHA-256 不同时，可以执行下面的比较。脚本检查 ZIP 完整性，比较解压后的部件，并列出 `docProps/` 属性差异。文档 XML、图表、图片、关系或其他内容部件有差异时转人工核验。本例应助副本仅 `docProps/custom.xml` 有差异，项目中保留了出版社原件。

```sh
python3 "$skill_dir/scripts/verify_files.py" compare-docx "$publisher_docx" "$response_docx"
```

视频检查验证 MP4 区块边界和视频轨道，并抽样解码。退出码 0 表示所选本地检查通过。退出码 1 会列出缺件、打不开的格式或需人工复核的证据，退出码 2 表示命令参数有误。通过后仍须核对原帖所求内容、正文是否完整及项目目标路径，再执行站内采纳。
