#!/usr/bin/env node
// Run beside a temporary installation of @ziuchen/wormhole-client.
import { mkdir, open, readFile, rmdir, unlink } from "node:fs/promises";
import { join, posix, win32 } from "node:path";
import { createDownloadClient } from "@ziuchen/wormhole-client/download";

function checkNames(files) {
  if (!files.length) throw new Error("收件包内未发现文件");
  const seen = new Set();
  for (const { name } of files) {
    if (!name || name === "." || name === ".." || posix.basename(name) !== name ||
        win32.basename(name) !== name || /[\u0000-\u001F:]/u.test(name)) {
      throw new Error("分享内含目录路径或特殊文件名，请在网页逐项收件");
    }
    const key = name.normalize("NFC").toLowerCase();
    if (seen.has(key)) throw new Error("收件包存在重名附件，请在网页逐项核对");
    seen.add(key);
  }

}

async function receive(receipt, destination) {
  const text = await readFile(receipt, "utf8");
  const links = new Set(text.match(/https:\/\/wormhole\.app\/[A-Za-z0-9]+#[A-Za-z0-9_-]+/g));
  if (links.size !== 1) throw new Error("请先确认本帖唯一的 Wormhole 收件链接");
  const [link] = links;

  // Reserve the destination before consuming a potentially limited share download.
  await mkdir(destination, { mode: 0o700 });
  const created = [];
  try {
    const { files } = await createDownloadClient().download(link);
    checkNames(files);
    for (const { name, data } of files) {
      const path = join(destination, name);
      const file = await open(path, "wx", 0o600);
      created.push(path);
      try {
        await file.writeFile(data);
      } finally {
        await file.close();
      }
      console.log(name, data.byteLength);
    }
    console.log("已收件", files.length, "项。请按出版社清单核对后归档。");
  } catch (error) {
    await Promise.allSettled(created.map(path => unlink(path)));
    await rmdir(destination).catch(() => {});
    throw error;
  }
}

const [receipt, destination] = process.argv.slice(2);
if (!receipt || !destination || process.argv.length !== 4) {
  console.error("用法：node receive-wormhole.mjs 本地说明.txt 新建的收件目录");
  process.exitCode = 2;
} else {
  try {
    await receive(receipt, destination);
  } catch (error) {
    const detail = String(error.message).replace(/https?:\/\/[^\s]+/gu, "[收件地址]");
    console.error("收件未完成。", detail);
    process.exitCode = 1;
  }
}
