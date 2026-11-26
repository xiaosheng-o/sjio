# 下载故障与网盘取件

## 科研通显示已接收，项目里没有文件

1. 核对当前下载页的文件名、大小、线路和进度。达到 100% 后点击“手动保存文件”，在保存对话框里选项目目标目录。浏览器自动命名时，检查默认下载目录的本次新增文件并核对其内容。
2. 如果页面变暗、出现广告或地址以 `#google_vignette` 结尾，先关闭广告。关闭控件无效时，可在该下载页后退一步。等页面重新显示可点击的“手动保存文件”，且文件仍然就绪，再保存一次。已接收的数据可以直接复用。
3. 当前浏览器工具支持 `downloadMedia` 时，可从已呈现的保存链接获得实际本机路径。在 Codex 浏览器工具中，对已绑定到**该附件**的 `tab` 执行下面的操作，再检查返回路径上的文件。

```javascript
const saveLink = tab.playwright.getByRole("link", { name: /手动保存文件/ });
const savedPath = await saveLink.downloadMedia({ timeout: 90000 });
nodeRepl.write(savedPath);
```

也可在点击前监听下载完成事件并取回文件路径。若系统保存窗口必须由用户操作，只请求完成当前保存步骤所需的操作。从原浏览器成功取得文件后，继续核验和归档。

## 应助附件是一份 TXT

从科研通手动保存说明，读取其中的收件链接，核对分享页的文件列表。先下载到临时目录，再和出版社清单逐项比对。带提取码或密钥的地址只在收件时使用。若链接过期、需要登录或内容缺失，记录具体情况，保持该帖待处理。

### Wormhole 网页未保存大文件时

原试验使用以下版本的第三方收件客户端取回了七个文件。说明明确提供 `wormhole.app` 收件链接、网页接收失败时，可用此方式。需要 Node.js 22.12 或更新版本及 npm。将 `receipt` 设为本地已保存的说明文件。随附的[收件脚本](../scripts/receive-wormhole.mjs)从本地读取密钥，只处理下载。软件和收到的附件都进入独立的临时目录。

```sh
skill_dir="${CODEX_HOME:-$HOME/.codex}/skills/ablesci-assist"
receipt="$PWD/补充材料/应助说明.txt"
work=$(mktemp -d)
npm install --prefix "$work" --no-save --ignore-scripts --no-audit --no-fund '@ziuchen/wormhole-client@0.0.0-b081b13' &&
  cp "$skill_dir/scripts/receive-wormhole.mjs" "$work/" &&
  node "$work/receive-wormhole.mjs" "$receipt" "$work/received"
```

收件目录须为新目录。脚本会列出每个文件及其实际字节数。若输出失败，保持帖子待处理。在本机 Node 需要使用系统受信任的证书时，可在支持该选项的版本使用 `node --use-system-ca` 执行同一命令。

核实下载结果后，按出版社文件名归档，并在项目目标目录复核。分享页文件名大小写可能与出版社不同。若同一份 Word 已从出版社获取，可用 `compare-docx` 将其和应助副本逐部件比对。
