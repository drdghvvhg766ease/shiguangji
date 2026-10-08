# 参与时光迹开发

## 开始之前

先按照 [README](./README.md#快速开始) 配置 Python、Node.js、MySQL 与本地环境变量。用户端代码位于 `frontend/user`，管理端位于 `frontend/admin`，后端位于 `backend`。

提交问题时请说明操作步骤、预期结果、实际结果和运行环境；截图或日志中的密码、令牌和私人内容请先删除。

## 修改与验证

- 保持修改聚焦，涉及功能或配置变化时同步更新文档。
- 两套前端分别维护锁文件；管理端会复用用户端的部分组件，修改共享组件后检查两端。
- 数据模型变化需要考虑旧数据库的迁移，迁移脚本放在 `backend`。
- API 集成测试使用独立数据库，并初始化 `seed.py` 和 `seed_admin.py`；测试会创建和删除账号、圈子与媒体。

前端检查，在 `frontend` 目录执行：

```bash
npm run ci:apps
npm run build
```

后端检查，在 `backend` 目录执行（PowerShell，API 已启动）：

```powershell
$env:API_BASE = 'http://127.0.0.1:8001'
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest test_enhancements.py test_social.py -q
```

提交 Pull Request 时说明修改原因、实际变化和验证结果。推送后可在 [Actions](https://github.com/drdghvvhg766ease/shiguangji/actions) 查看自动检查。

## Git 提交与贡献者显示

提交说明应简短描述具体变化，例如 `docs: clarify backend setup` 或 `fix: preserve circle media permissions`。

GitHub 的 Contributors 由提交记录自动统计。若希望提交关联到你的 GitHub 账号，在提交前将 Git 作者邮箱设置为该账号已验证的邮箱，或 GitHub 邮箱设置页面提供的 noreply 地址。可用以下命令检查当前配置：

```bash
git config user.name
git config user.email
```

本地 `.env`、上传媒体、备份、日志、依赖与构建目录已通过 `.gitignore` 排除；可提交的环境变量模板为 `backend/.env.example`。
