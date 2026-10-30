# EvoTool 推送 GitHub 流程

当用户要求“按照仓库内的推送流程推送”时，执行本文档。仓库远端为：

- 本地仓库：`D:\Evotool`
- GitHub 远端：`https://github.com/bofanli87-ai/ACL_2026_EvoTool.git`
- 本地分支：`master`
- 目标分支：`origin/main`

## 1. 检查改动

在仓库根目录执行：

```powershell
git status --short
git diff --stat
git diff --check
```

确认所有已修改、新增和删除的文件都应包含在本次提交中。不要读取、显示或写入用户的 GitHub Token。

## 2. 运行可用的测试

优先尝试项目虚拟环境：

```powershell
.venv\Scripts\python.exe -m pytest -q
```

如果缺少 `pytest` 或其他依赖，应如实记录，不要仅为推送而擅自安装依赖。测试失败时先说明原因，并根据用户要求决定是否继续提交。

## 3. 暂存并提交

```powershell
git add -A
git diff --cached --stat
git diff --cached --check
git commit -m "简洁描述本次改动"
```

提交后记录提交哈希，并再次执行 `git status -sb`。

## 4. 通过 CLI 输入账号和 Token

本机旧版 Git Credential Manager 的图形登录窗口可能崩溃，因此推送时临时禁用凭据助手，并打开一个用户可见的 CLI：

```powershell
Start-Process -FilePath "cmd.exe" -ArgumentList '/k','cd /d D:\Evotool && git -c credential.helper= push origin HEAD:main'
```

用户在新窗口中：

1. 输入 GitHub 用户名。
2. 在密码提示处粘贴 GitHub Personal Access Token；输入时不显示字符属于正常现象。
3. 按 Enter，等待出现推送成功信息。

Token 只由用户在可见 CLI 中输入。不要让用户把 Token 发到聊天中，也不要把 Token 写进远端 URL、仓库文件、命令记录或 Git 配置。

## 5. 核验推送结果

用户确认 CLI 推送成功后执行：

```powershell
git status -sb
git log -1 --oneline --decorate
git ls-remote origin refs/heads/main
```

核对本地 `HEAD`、`origin/main` 和远端 `refs/heads/main` 的提交哈希一致。最后向用户报告提交哈希、目标分支、工作区状态和测试结果。

## 本次成功记录

2026-10-24，提交 `4fb3fbb` 已通过上述交互式 Token 流程成功推送到 `origin/main`。
