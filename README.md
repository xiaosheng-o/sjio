# 科研通文献求助 Skill

通过 Codex 使用科研通（AbleSci）发布和跟进文献求助，将正文与补充材料存入当前项目，核验后分别采纳。

技能入口为 [SKILL.md](SKILL.md)。支持 macOS、Windows 和 Linux 上具备浏览器控制能力的 Codex 环境。论文核验使用 Python 3.9 或更新版本，视频核验使用 FFmpeg；macOS 也支持系统自带的 avconvert。Wormhole 收件备用方案需要 Node.js 22.12 或更新版本及 npm。

## 在另一台设备安装

仓库地址为 https://github.com/xiaosheng-o/sjio，安装目录统一命名为 `ablesci-assist`。

### macOS 与 Linux

```sh
skill_home="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skill_home"
git clone https://github.com/xiaosheng-o/sjio.git "$skill_home/ablesci-assist"
cd "$skill_home/ablesci-assist"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

视频核验需能在 PATH 中找到 `ffmpeg`。macOS 可使用系统 avconvert。用发行版包管理器安装 FFmpeg 后执行 `ffmpeg -version` 确认。

### Windows PowerShell

```powershell
$skillHome = Join-Path $HOME ".codex/skills"
if ($env:CODEX_HOME) { $skillHome = Join-Path $env:CODEX_HOME "skills" }
New-Item -ItemType Directory -Force $skillHome | Out-Null
git clone https://github.com/xiaosheng-o/sjio.git (Join-Path $skillHome "ablesci-assist")
Set-Location (Join-Path $skillHome "ablesci-assist")
py -3 -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

安装 Git 和 Python 后再运行。需要视频核验时安装 FFmpeg，并在重新打开的终端中运行 `ffmpeg -version`。使用虚拟环境的 Python 可直接运行核验脚本，无需激活环境。

完成安装后，在新对话中调用 `$ablesci-assist`。每台设备分别登录科研通，按该设备环境启用浏览器控制。在新的项目中给出保存目录和是否需要补充材料。

## 使用

> 用 $ablesci-assist 获取 DOI 为……的论文正文和全部补充材料，保存到当前项目，核验后分别采纳。

> 用 $ablesci-assist 检查本项目在科研通的待确认求助，下载并核对文件后采纳。

工作流程包括校园网实际访问检查、查找已有帖子、分帖求助、高速通道手动保存、核验和采纳。只查询现有帖子时从“我的求助 → 待确认”开始。跨设备接手续办时携带项目中记录的 DOI、帖链接、所求类型、官方附件清单和最新状态，并先检查原帖。浏览器登录状态及定时检查任务在各设备单独配置。

本次应助和最终归档各自核验，旧目录中已有的视频不会掩盖本次应助漏交的项目。后台检查需要当前宿主的调度能力，按用户约定设置频率。

## 本地核验

macOS / Linux 使用安装目录下的 `.venv/bin/python`，Windows 使用 `.venv/Scripts/python.exe`。命令中的输入文件应为本次实际收件。

```sh
.venv/bin/python scripts/verify_files.py paper "/path/to/paper.pdf" --title "Exact paper title" --doi "10.xxxx/example"
.venv/bin/python scripts/verify_files.py si "/path/to/补充材料" --expected "/path/to/publisher-files.txt" --title "Exact paper title"
.venv/bin/python scripts/verify_files.py compare-docx "/path/to/publisher.docx" "/path/to/response.docx"
```

官方附件清单为 UTF-8 文本，每行一个文件名，可在制表符后附精确字节数。样例、核验范围和退出码见 [references/verify.md](references/verify.md)。浏览器广告与下载故障、Wormhole 备用取件见 [references/downloads.md](references/downloads.md)。扫描件、单页文章和部分附件格式需要人工打开复核。

## 更新

在已安装的技能目录执行 `git pull --ff-only`，再使用该目录虚拟环境的 Python 执行 `-m pip install -r requirements.txt`。每台设备分别更新。若本地改动导致 Git 停止，先保留并处理这些改动。

## 仓库内容

- `SKILL.md` 和 `agents/openai.yaml` 提供技能指令与调用信息。
- `scripts/verify_files.py` 核对正文、补充材料清单与 Word 副本。
- `scripts/receive-wormhole.mjs` 提供可选的 Wormhole 收件。
- `references/` 保存故障处理、核验命令和官方附件文件名样例。

论文与附件保存在各自项目中。下载的文献使用范围按来源授权和平台要求处理。
