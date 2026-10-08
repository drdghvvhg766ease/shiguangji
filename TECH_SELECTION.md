# 「时光迹」开源框架选型说明

> 开发前选型记录 · 对应毕业设计方案 V7 第 8 节  
> 核对环境：本机 hosts 将 github.com 指向 127.0.0.1，无法直连 GitHub；下列仓库均通过 **npmmirror / 清华 PyPI 镜像** 核验包名、最新版本与许可证，与 GitHub 上游仓库一一对应。

## 选型结论

| 层 | 选用开源项目 | GitHub 上游 | 许可 | 镜像核验版本 | 理由 |
|----|--------------|-------------|------|--------------|------|
| 后端框架 | FastAPI | `fastapi/fastapi` | MIT | 0.112.0 | 异步 REST、自动 OpenAPI 文档，适合答辩展示接口证据 |
| ORM | SQLAlchemy 2.x | `sqlalchemy/sqlalchemy` | MIT | 2.0.32 | 方案指定；声明式模型 + 事务清晰 |
| 数据库驱动 | PyMySQL | `PyMySQL/PyMySQL` | MIT | 1.1.1 | 纯 Python，MySQL 8.4 兼容 |
| JWT | python-jose | `mpdavis/python-jose` | MIT | 1.0.0 | JWT 签发/校验，配合 HttpOnly Cookie |
| 密码哈希 | passlib[bcrypt] | `pyca/passlib` | BSD-3 | 1.7.4 | 成熟口令哈希 |
| 上传解析 | python-multipart | `Kludex/python-multipart` | Apache-2.0 | 0.0.9 | FastAPI multipart 表单依赖 |
| 图片处理 | Pillow | `python-pillow/Pillow` | MIT-CMU | 10.4.0 | 生成照片缩略图，不改动原图 |
| 前端框架 | Vue 3 | `vuejs/core` | MIT | 3.x | 方案指定 SPA 技术栈 |
| 构建 | Vite | `vitejs/vite` | MIT | 5.x/6.x | 开发代理 `/api`，生产静态资源 |
| 路由 | Vue Router | `vuejs/router` | MIT | 4.x | 页面路由 |
| 状态 | Pinia | `vuejs/pinia` | MIT | 2.x | 当前圈子、登录态 |
| HTTP | Axios | `axios/axios` | MIT | 1.x | `withCredentials` 携带 JWT Cookie |
| 粒子动效 | tsParticles + @tsparticles/vue3 | `tsparticles/tsparticles` | **MIT** | engine/vue3 **4.4.0** | 方案指定；Vue 3 官方组件；登录背景 + 投稿成功反馈 |

## tsParticles 许可与兼容性核对

- 仓库：https://github.com/tsparticles/tsparticles  
- 许可：**MIT**（镜像元数据确认）  
- Vue 3 官方组件：`@tsparticles/vue3`（描述含 “Vue.js 3.x Component”）  
- 引擎：`@tsparticles/engine`，主页 https://particles.js.org  
- 二次开发方式：不 fork 源码，以 npm 依赖引入，在业务侧用配置对象定制「细小纸屑」效果；保留 MIT 许可声明于 `frontend/user/src/assets/tsparticles-LICENSE.txt`  
- 降级：`prefers-reduced-motion` 时关闭动画；移动端降低粒子数量

## 明确不用的方案

| 候选 | 不用原因 |
|------|----------|
| Django + DRF | 偏重、约定过多，方案指定 FastAPI |
| MongoDB / SQLite 作为主库 | 方案指定 MySQL（utf8mb4 中文/表情） |
| NestJS / Express 后端 | 方案要求 Python 后端 |
| particles.js（原版） | 已停更，Vue 3 官方支持弱于 tsParticles |
| full-stack 模板一键 clone | GitHub 不可直连；按方案目录结构手写更贴合毕设答辩 |

## 本地服务核对结果

| 组件 | 状态 |
|------|------|
| Python 3.12.13 | 可用（MiMo runtime） |
| Node.js v24.15.0 | 可用 |
| MySQL 8.4.9 | 运行中，连接信息由本地 `.env` 配置 |
| FFmpeg | **未预装** → 运行时探测 `ffmpeg/ffprobe`，缺失时跳过视频封面并提示安装 |

## 运行环境约束

- 本机 hosts 屏蔽了 github.com 及相关域名，开发安装依赖请使用：
  - npm：`https://registry.npmmirror.com`
  - pip：`https://pypi.tuna.tsinghua.edu.cn/simple`
- 如需克隆 GitHub 源码做二次开发，请先解除 hosts 屏蔽或走公司代理。
