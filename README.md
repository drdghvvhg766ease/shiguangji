# 时光迹 · 朋友照片 / 生活记录平台

毕业设计方案 V7 对应实现：私密朋友圈 + 生活痕迹线 + 共同相册 + 主题分册接力 / 猜照片。  
不接入 AI、无推荐算法、无公开广场。

代码位置：`F:\moments`

## 开源选型

详见 [TECH_SELECTION.md](./TECH_SELECTION.md)。

| 层 | 选型 |
|----|------|
| 后端 | Python · FastAPI · SQLAlchemy 2 · JWT HttpOnly Cookie |
| 数据库 | MySQL 8.4 · utf8mb4 · PyMySQL |
| 前端 | Vue 3 · Vite · Pinia · Axios · Leaflet |
| 粒子 | tsParticles / @tsparticles/vue3（MIT，登录背景 + 投稿反馈） |
| 媒体 | 原文件字节保存 + Pillow 缩略图 + 可选 FFmpeg 视频封面 |

## 快速开始

### 1. 准备 MySQL

已安装 MySQL 8.x，并准备一个账号（示例写在本地 `.env`，**不要提交**）。

```sql
-- 可选：程序会自动 CREATE DATABASE shiguangji
CREATE DATABASE IF NOT EXISTS shiguangji CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 后端

```powershell
cd F:\moments\backend
# 创建独立环境并安装依赖
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 写本地环境变量（按需修改密码）
# 编辑 .env 中的 MYSQL_PASSWORD

# 建表；已有数据库也可运行（不会覆盖数据）
.\.venv\Scripts\python.exe -c "from app.database import ensure_database, init_db; ensure_database(); init_db()"
# 升级已有数据结构，举报迁移会先备份 reports
.\.venv\Scripts\python.exe migrate_reports.py
.\.venv\Scripts\python.exe migrate_lines.py
.\.venv\Scripts\python.exe migrate_activity.py
.\.venv\Scripts\python.exe migrate_social.py
# 仅在需要初始化演示数据时执行 seed.py / seed_admin.py

# 启动 API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

接口文档：http://127.0.0.1:8001/docs

### 3. 前端

```powershell
cd F:\moments\frontend
# 使用国内 npm 镜像
npm config set registry https://registry.npmmirror.com
npm run install:apps
npm run dev
```

浏览器打开：http://localhost:5173

管理端在 `frontend` 目录执行 `npm run dev:admin`，访问 http://localhost:5174。

用户端和管理端分别位于 `frontend/user`、`frontend/admin`，也可进入各自目录执行 `npm install`、`npm run dev`。在 `frontend` 目录执行 `npm run build` 会构建两端，产物分别写入 `user/dist`、`admin/dist`。

安装好前后端依赖后，可运行根目录的 `start-dev.bat` 同时启动 API、用户端和管理端。

### 4. 测试（可选）

```powershell
# 先保证 8001 端口 API 已启动
cd F:\moments\backend
$env:API_BASE = 'http://127.0.0.1:8001'
.\.venv\Scripts\python.exe -m pytest test_enhancements.py -q
```

云主机部署见 [`deploy/DEPLOY.md`](./deploy/DEPLOY.md)。视频封面需 FFmpeg：`deploy/install-ffmpeg.ps1`。

## 艺术影集与共享时间线

- 照片墙、时间线、共同相册统一使用记录详情，可浏览全部照片、播放视频、下载原文件、评论、编辑自己的记录及举报。
- 每个朋友圈有一条汇总主线。成员可新建生活、旅行、毕业等时间线，并建立下级分支；父线汇总其所有后代分支。
- 分册可关联一条时间线，一条时间线可关联多本分册。分册归属优先于记录单独选择的时间线，调整分册归属会同步影响其记录的展示位置。
- 发布或编辑记录可选择城市、地图打点或输入经纬度。足迹地图按生活日期连接地点；当前时间线、年份筛选同时作用于地图。
- 删除分册或时间线不删除原记录和媒体；删除朋友圈则删除圈内内容与原文件，仅圈主可操作。时间线和分册由创建者或圈主管理。
- 图片详情支持方向键、手机轻扫和 Escape 关闭；发布支持真实上传进度、照片排序及未发布内容保护。

本轮工作记录、迁移说明与验证结果见 [docs/2026-10-01-工作记录.md](./docs/2026-10-01-工作记录.md)。

## 演示账号

| 账号 | 密码 | 角色 |
|------|------|------|
| demo_a | demo1234 | 圈主「我们仨」 |
| demo_b | demo1234 | 成员 |

邀请码：`DEMO2026`

## 功能对照（MVP）

- [x] 注册 / 登录（JWT HttpOnly Cookie）
- [x] 自建朋友圈 · 邀请码加入 · 多圈切换 · 转让 / 解散
- [x] 发布 1～9 张照片 **或** 1 段短视频 + 文字 + 生活日期 + 标签 + 分册
- [x] 原文件字节保存、SHA-256、缩略图 / 视频封面
- [x] 照片墙（拍立得卡片流）
- [x] 生活痕迹线（按日/月竖向时间轴）
- [x] 共同相册（成员 / 月份 / 标签筛选）
- [x] 主题分册（拼贴封面、接力题目、参与成员）
- [x] 猜猜那天（前端抽签 / 揭晓，不落库）
- [x] 痕迹详情：大图 / 视频播放、逐张导出原图、视频原文件下载、评论
- [x] Web 粒子动效（登录背景 + 投稿成功反馈；`prefers-reduced-motion` 降级）
- [x] 视频 Range（206）拖动播放
- [x] 非成员无法访问圈内媒体

## 目录结构

```
moments/
  TECH_SELECTION.md
  README.md
  start-dev.bat
  backend/
    requirements.txt
    seed.py
    smoke_test.py
    .env                 # 本地密钥，勿提交
    app/
      main.py
      config.py
      database.py
      models.py
      schemas.py
      security.py
      media_utils.py
      routers/
        auth.py
        circles.py
        posts.py
        album.py
        media.py
        comments.py
    uploads/             # 原文件 + 预览，经鉴权接口读取
  frontend/
    package.json         # 两端的统一安装、启动和构建命令
    user/                # 用户端，开发端口 5173
      package.json
      vite.config.js
      public/
      src/
        main.js
        App.vue
        api.js
        stores/auth.js
        styles.css
        views/...
        assets/tsparticles-LICENSE.txt
    admin/               # 管理端，开发端口 5174
      package.json
      vite.config.js
      src/
        AdminApp.vue
        main.js
        api.js
  deploy/                # 部署配置与说明
  docs/                  # 需求与工作记录
  scripts/               # 开发辅助脚本
  tests/                 # 浏览器集成测试及共享媒体样本
```

## 媒体规则（与方案一致）

- 照片：JPEG / PNG / WebP，单张 ≤10 MB，每条 ≤9 张
- 视频：MP4 / MOV，单段 ≤100 MB / 3 分钟；照片与视频不混传
- 原图 / 原视频按上传字节保存，不压缩不改尺寸；下载 SHA-256 与上传一致
- `uploads/` 不作为公开静态目录；全部经 `/api/media/...` 成员鉴权
- FFmpeg 可选：缺失时跳过视频封面，不影响原文件保存与下载

## 部署提示（Oracle Always Free）

1. Nginx 托管 `frontend/user/dist`，并反代 `/api` → uvicorn；管理端产物位于 `frontend/admin/dist`，可用独立站点托管
2. `uploads/` 放持久盘，与程序发布目录分离
3. HTTPS 开启后把 `.env` 中 `COOKIE_SECURE=true`
4. MySQL 只监听本机 / 内网；定期备份数据库与 `uploads/`
5. Nginx `client_max_body_size` ≥ 100m

## 视觉

- 明亮中性背景、朱砂点缀与灰绿辅助色；艺术影集照片墙、月度生活影集与中国足迹地图。
- 圈子的生活痕迹线由成员共享，分支可关联分册；个人主页的“我的痕迹线”记录本人参与圈子的操作，按操作时间排列，可筛选圈子、年份和类型。
- 个人操作与业务数据一起提交，失败操作不写成功历史，退出或解散圈子后仍保留本人的历史摘要；访问记录与媒体仍检查当前成员权限。
- `migrate_activity.py` 只回填旧数据可确认的创建、加入等事件，不能还原旧编辑与删除历史。最新记录见 `docs/2026-10-01-工作记录.md`。
- 圈子支持圈主、管理员和普通成员；所有成员可邀请，新增成员须经圈主或管理员审核，通过后可见历史内容。
- 个人主页提供头像裁剪、昵称/密码设置、消息中心与多个收藏夹；收藏夹默认私密，可向指定圈子分享，原记录权限继续生效。
- `migrate_social.py` 升级角色、申请、消息、回复、点赞与收藏表，保留已有成员和媒体。记录和分册同时关联多个分支的功能暂缓。
- 生活影集增加照片胶片导航、上一刻/下一刻、随机回忆、当前记录与浏览进度；地点选择支持本地 370 个城市/地区和省份搜索，仍可地图点选与手填坐标。
- 用户端和管理台使用不同登录会话：管理台登录/退出/身份查询改为 `/api/admin/auth/...`，审核媒体使用 `/api/admin/media/...`，避免同一浏览器打开两端时覆盖用户身份。升级后两端分别重新登录一次。
