# 不用命令行的发布方式

如果你的电脑连不上 GitHub、或者不想用命令行，用下面任一方式。

---

## 方式一：GitHub Desktop（最简单，推荐）

1. 下载安装 <https://desktop.github.com/>
2. 打开后 **File → Add local repository…**
3. 选择 `D:\desktop\ds-chat\a`（这个目录已经初始化好 git，会直接识别）
4. 右上角点 **Publish repository**
   - Name：`personal-api-chat-client`
   - 取消勾选 **Keep this code private**
   - 点 **Publish repository**
5. 等它上传完成，浏览器打开仓库确认

> 发布后如果提示登录，用 GitHub 账号授权即可，不需要手输 Token。

---

## 方式二：网页上传（不需要 Git）

适合只想把源码放上去、不关心提交历史的情况。

### 步骤

1. GitHub → **New repository**
   - Name：`personal-api-chat-client`
   - Public
   - **不要**勾 Add a README / .gitignore / license
2. 进入空仓库页面，点 **uploading an existing file**
3. 打开资源管理器，进入 `D:\desktop\ds-chat\a`
4. **先删掉/不要选**这些（它们不该上传）：
   - `dist\`、`build\`、`backup\`、`diagnostics\`、`aaaaa\`
   - `config.enc`、`chat_history.json`、`settings.json`、`debug.log`
5. 选中剩下的**文件和文件夹**，直接拖进浏览器上传区
   - Chrome / Edge 支持拖文件夹（会自动展开子文件）
   - 如果浏览器不支持，就先建目录再分批上传
6. 底部 Commit changes 填 `Initial commit`，提交

### 注意

- 网页上传**不会**带上 `.git`，所以没有提交历史，也不能再命令行 push 覆盖——后续要么一直网页改，要么重新 clone。
- 单个文件 < 25 MB（本项目最大是 238 KB 的 `deepseek_chat.py`，没问题）。
- `assets/logos/` 有 66 个 PNG，拖文件夹最省事。

---

## 方式三：把项目打包带走，在有网的电脑上推

1. 把 `D:\desktop\ds-chat\a` 整个目录拷到 U 盘
2. 在能上网的电脑上打开该目录
3. 双击 **`push.bat`**（会自动检查网络、配置 remote、推送 main、打标签）

前提：那台电脑装了 Git for Windows，并且你已经在那台电脑上登录过 GitHub
（`git config --global credential.helper manager` 会弹窗登录一次）。

---

## 三种方式怎么选

| 情况 | 推荐 |
|---|---|
| 电脑能上网，只想省事 | 方式一 GitHub Desktop |
| 完全不想装任何工具 | 方式二 网页上传 |
| 要保留完整提交历史 | 方式三 拷贝到有网电脑跑 `push.bat` |

无论哪种，最后都别忘了：

**Releases → Draft a new release → 标签 v1.0.0 → 上传 `dist\PersonalAPIChatClient-V1.0-portable-win64.zip`**
