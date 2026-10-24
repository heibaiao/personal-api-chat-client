# 开源发布流程（完整版）

面向本仓库：`heibaiao/personal-api-chat-client`
目标：把本地 `D:\desktop\ds-chat\a` 变成一个可长期维护的公开仓库，并能持续发版。

---

## 0. 一次性准备

| 项 | 说明 |
|---|---|
| GitHub 账号 | `heibaiao` |
| Git for Windows | <https://git-scm.com/download/win>（安装后 `git --version` 能输出版本） |
| Python 3.10+ | 仅本地打包需要，普通用户下载 Release 即用 |
| GitHub CLI（可选） | <https://cli.github.com/>，装完 `gh auth login` 可命令行建仓库、发 Release |

安装后建议先设一次身份和换行策略：

```powershell
git config --global user.name  "heibaiao"
git config --global user.email "你的邮箱"
git config --global core.quotepath false     # 中文文件名不转义
git config --global init.defaultBranch main
```

---

## 1. 发布前检查（最重要的一步）

### 1.1 确认没有密钥泄漏

```powershell
cd D:\desktop\ds-chat\a

# 源码里不应有真实 Key
Select-String -Path deepseek_chat.py -Pattern 'sk-[A-Za-z0-9]{16,}'

# 文档/脚本里不应有占位符残留
Get-ChildItem -Recurse -Include *.md,*.py,*.bat |
  Select-String -Pattern '<your-|your-email|your-name'
```

两条都应**无输出**。

### 1.2 确认隐私文件不会被提交

必须被 `.gitignore` 挡住：

```
config.enc          API Key 加密库
chat_history.json   对话记录
settings.json       个人设置
debug.log           运行日志
dist/  build/       构建产物（229 MB，绝不能进历史）
backup/ diagnostics/ aaaaa/   本地素材与旧版
```

### 1.3 确认体积

```powershell
Get-ChildItem -Recurse -File |
  Where-Object { $_.FullName -notmatch '\\dist\\|\\build\\|\\backup\\|\\diagnostics\\|\\aaaaa\\' } |
  Measure-Object Length -Sum |
  ForEach-Object { "{0} files, {1:N2} MB" -f $_.Count, ($_.Sum/1MB) }
```

预期：约 **86 个文件 / 0.5 MB**（不含 Release 附件）。

---

## 2. 版本号与命名规则

| 名称 | 规则 | 示例 |
|---|---|---|
| 对外版本 | `V1.0`（关于页、窗口标题） | `V1.0` |
| Git 标签 | `v主.次.修订`，与对外版本对应 | `v1.0.0` |
| 发布包 | `PersonalAPIChatClient-<对外版本>-portable-win64.zip` | `PersonalAPIChatClient-V1.0-portable-win64.zip` |
| 包内 exe | `PACC-<对外版本>.exe`（PACC = Personal API Chat Client 缩写） | `PACC-V1.0.exe` |

发版前同步两处：`APP_VERSION_PUBLIC` 与 `version_info.txt` 的 `FileVersion/ProductVersion`。

---

## 3. 初始化本地仓库

```powershell
cd D:\desktop\ds-chat\a
git init
git branch -M main
git add .
git status --short
```

**逐行检查 `git status` 输出**，出现下列任意一项立即停下：

- `config.enc` / `chat_history.json` / `settings.json` / `debug.log`
- `dist/` / `build/` / `backup/` / `diagnostics/` / `aaaaa/`

若已误加：

```powershell
git rm -r --cached dist
```

然后提交：

```powershell
git commit -m "Initial commit: Personal API Chat Client V1.0"
```

---

## 4. 创建 GitHub 仓库

### 方式 A：网页

GitHub → **New repository**：

| 字段 | 填 |
|---|---|
| Repository name | `personal-api-chat-client` |
| Description | `单文件 Tkinter 桌面 AI 对话客户端 · 37 个 OpenAI 兼容模型 · 实时渲染 · 用量计费` |
| Visibility | **Public** |
| Add a README | 不勾（本地已有） |
| Add .gitignore | 不选（本地已有） |
| Choose a license | 不选（本地已有 MIT） |

### 方式 B：命令行（gh CLI）

```powershell
gh repo create personal-api-chat-client --public `
  --description "单文件 Tkinter 桌面 AI 对话客户端 · 37 个 OpenAI 兼容模型" `
  --source . --remote origin --push
```

---

## 5. 首次推送

```powershell
git remote add origin https://github.com/heibaiao/personal-api-chat-client.git
git push -u origin main
```

SSH 写法：

```powershell
git remote add origin git@github.com:heibaiao/personal-api-chat-client.git
```

---

## 6. 仓库基础设置

在仓库页面完成这些一次性配置：

| 位置 | 设置 |
|---|---|
| About（右侧齿轮） | Description 同上；Topics 填 `python` `tkinter` `openai` `llm` `desktop-app` `chatbot` `markdown` `windows` |
| Settings → General | 确认默认分支 `main`；开启 Issues |
| Settings → Actions → General | Workflow permissions 设为 **Read and write**（CI 才能上传 Release 资产） |
| Settings → Security | 开启 Dependabot alerts |
| Security → Policy | 会自动读取 `SECURITY.md` |
| Settings → Branches | 可选：给 `main` 加保护规则，禁止直接 push |

---

## 7. 打标签并发布 Release

### 7.1 构建发布包

```powershell
build.bat
```

产物：

```
dist\PersonalAPIChatClient-V1.0-portable\PACC-V1.0.exe
dist\PersonalAPIChatClient-V1.0-portable-win64.zip
```

### 7.2 打标签

```powershell
git tag -a v1.0.0 -m "V1.0"
git push origin v1.0.0
```

### 7.3 创建 Release

网页：**Releases → Draft a new release**

| 字段 | 填 |
|---|---|
| Choose a tag | `v1.0.0` |
| Release title | `V1.0` |
| 描述 | 粘贴 `docs/RELEASE_NOTES_v1.0.0.md` 的内容 |
| Attach binaries | 上传 `PersonalAPIChatClient-V1.0-portable-win64.zip` |

命令行等价：

```powershell
gh release create v1.0.0 `
  dist\PersonalAPIChatClient-V1.0-portable-win64.zip `
  --title "V1.0" --notes-file docs\RELEASE_NOTES_v1.0.0.md
```

---

## 8. 发布后验证

按“陌生人视角”走一遍：

- [ ] README 里的 2 个链接可点：Releases 页、clone 地址
- [ ] 下载 zip → 解压 → 双击 `PACC-V1.0.exe` 能启动
- [ ] 首页截图正常显示（`docs/screenshots/*.png` 未 404）
- [ ] 首次启动能走完“选模型 → 填 Key → 设密码”
- [ ] 关于页能看到版本号 V1.0 与已知问题清单
- [ ] `LICENSE`、`SECURITY.md`、`CONTRIBUTING.md` 在仓库首页可访问

---

## 9. 日常迭代发布流程

每次改代码（修 bug、加功能、改文档）都按这个顺序：

```powershell
# ① 改代码
# ② 同步关于页（FEATURE_GROUPS / 已知问题）——本项目硬规则
# ③ 回归自测
python -m py_compile deepseek_chat.py
python deepseek_chat.py        # 手动：发消息、流式、切模型、设置、导出

# ④ 重新打包
build.bat

# ⑤ 更新 CHANGELOG.md（写清改了什么）
# ⑥ 提交
git add .
git commit -m "fix: 修复 xxx"
git push

# ⑦ 发版（版本号递增，例如 v1.0.1）
git tag -a v1.0.1 -m "V1.0.1"
git push origin v1.0.1
# ⑧ Releases 页上传新 zip
```

### 提交信息约定

| 前缀 | 用途 |
|---|---|
| `feat:` | 新功能 |
| `fix:` | 修 bug |
| `docs:` | 只改文档 |
| `refactor:` | 重构 |
| `build:` | 打包脚本 / 依赖 |

### 只改文档时

不需要重新打包（`dist/` 里的 zip 仍有效），但 README 与关于页描述必须一致。

---

## 10. 常见故障排查

| 现象 | 原因 | 解决 |
|---|---|---|
| `repository not found` | 网页上还没建仓库，或地址写错 | 先建仓库；核对 `git remote -v` |
| `non-fast-forward` | 远端有初始提交 | `git pull --rebase origin main` 后重推 |
| `src refspec main does not match any` | 还没有任何提交 | 先 `git add . && git commit` |
| 仓库莫名 100 MB+ | 误提交 `dist/` | `git rm -r --cached dist` 提交；历史清理用 `git filter-repo --path dist --invert-paths` |
| 中文文件名显示为 `\346\226\207` | 未设 quotepath | `git config --global core.quotepath false` |
| 每个文件都显示改动 | 换行符差异 | 已含 `.gitattributes`，必要时 `git add --renormalize .` |
| push 要求密码 | GitHub 已禁用密码认证 | 用 Personal Access Token 或 SSH key |
| Release 附件上传失败 | 超过 2 GB 或网络中断 | 本项目 56 MB，正常；重试即可 |
| Actions 无法上传资产 | 权限默认只读 | Settings → Actions → Read and write |

---

## 11. 附：可选增强

- **CI**：`.github/workflows/build.yml` 在推 `v*` 标签时自动构建 Windows 包并上传 artifact
- **Issue 模板**：`.github/ISSUE_TEMPLATE/` 已有 bug / feature 两个表单
- **PR 模板**：`.github/PULL_REQUEST_TEMPLATE.md` 带自查清单（含“关于页已同步”）
- **回滚**：`git revert <commit>`，或删掉错误 tag（`git tag -d v1.0.1 && git push origin :refs/tags/v1.0.1`）后重发

---

## 12. 一键速查（首次发布）

```powershell
cd D:\desktop\ds-chat\a
Select-String -Path deepseek_chat.py -Pattern 'sk-[A-Za-z0-9]{16,}'   # 应无输出
git init; git branch -M main
git add .; git status --short                                          # 核对清单
git commit -m "Initial commit: Personal API Chat Client V1.0"
git remote add origin https://github.com/heibaiao/personal-api-chat-client.git
git push -u origin main
git tag -a v1.0.0 -m "V1.0"; git push origin v1.0.0
# 最后在 Releases 页上传 dist\PersonalAPIChatClient-V1.0-portable-win64.zip
```
