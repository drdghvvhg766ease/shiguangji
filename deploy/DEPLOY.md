# 部署到 Oracle Cloud Always Free

## 目录规划

| 路径 | 用途 |
|------|------|
| `/opt/shiguangji/backend` | 后端代码 + venv |
| `/opt/shiguangji/backend/.env` | 环境变量（600 权限） |
| `/var/www/shiguangji/dist` | 前端构建产物 |
| `/data/shiguangji/uploads` | 媒体持久盘（备份源） |
| `/etc/nginx/sites-available/shiguangji` | Nginx 站点 |

## 步骤

1. 上传代码，进入 `backend/` 安装依赖：`python3 -m venv venv && venv/bin/pip install -r requirements.txt`
2. 复制 `.env.example` 为 `.env`，填写 MySQL 密码与随机 `JWT_SECRET`
3. 建库与建表：`venv/bin/python -c "from app.database import ensure_database, init_db; ensure_database(); init_db()"`；已有旧数据库先备份，再按根目录 README 的顺序执行迁移。`seed.py`、`seed_admin.py` 用于演示账号与数据初始化
4. 在项目的 `frontend/` 目录执行 `npm run ci:apps`、`npm run build`，将 `frontend/user/dist/` 上传到 `/var/www/shiguangji/dist`；管理端产物 `frontend/admin/dist/` 可另行配置独立 Nginx 站点托管
5. 放置 `deploy/nginx.conf`，`nginx -t && systemctl reload nginx`
6. 放置 `deploy/shiguangji.service`，`systemctl enable --now shiguangji`
7. 配 HTTPS 后：`.env` 中 `COOKIE_SECURE=true`，`ALLOWED_ORIGINS` 填写用户端与管理端的实际来源（逗号分隔），Nginx 监听 443
8. 备份：`/var/lib/mysql` 或 `mysqldump` + `/data/shiguangji/uploads`

## 注意

- MySQL 不要对公网开放 3306
- 视频会更快占满免费磁盘，先保持 100MB / 3 分钟限制并监控 `df -h`
- 免费实例可能因容量不足无法创建，答辩保留本地 MySQL 兜底
