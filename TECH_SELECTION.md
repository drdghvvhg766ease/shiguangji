# 时光迹技术选型

项目采用 Vue 前端、FastAPI 后端与 MySQL 数据库。用户端和管理端共享后端 API，分别构建和部署。

## 依赖与用途

下表列出当前依赖文件声明的版本范围；前端实际安装版本由各应用的 `package-lock.json` 固定。Python 依赖以 `backend/requirements.txt` 为准。

| 技术 | 声明版本 | 用途 | 上游 |
| --- | --- | --- | --- |
| Vue | `^3.5.12` | 用户端与管理端组件 | [vuejs/core](https://github.com/vuejs/core) |
| Vite | `^5.4.10` | 开发服务、API 代理和生产构建 | [vitejs/vite](https://github.com/vitejs/vite) |
| Pinia | `^2.2.4` | 账号与圈子状态 | [vuejs/pinia](https://github.com/vuejs/pinia) |
| Axios | `^1.7.7` | 携带 Cookie 的 HTTP 请求 | [axios/axios](https://github.com/axios/axios) |
| Leaflet | `^1.9.4` | 本地地图边界与足迹展示 | [Leaflet/Leaflet](https://github.com/Leaflet/Leaflet) |
| tsParticles engine / Vue | `^4.4.0` | 登录背景与发布反馈动效 | [tsparticles/tsparticles](https://github.com/tsparticles/tsparticles) |
| FastAPI | `>=0.112.0` | REST API、参数验证与 OpenAPI 文档 | [fastapi/fastapi](https://github.com/fastapi/fastapi) |
| SQLAlchemy | `>=2.0.32` | 数据模型、查询与事务 | [sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) |
| PyMySQL | `>=1.1.1` | MySQL 数据库连接 | [PyMySQL/PyMySQL](https://github.com/PyMySQL/PyMySQL) |
| python-jose | `>=3.3.0` | JWT 签发与校验 | [mpdavis/python-jose](https://github.com/mpdavis/python-jose) |
| passlib / bcrypt | `>=1.7.4` / `>=4.0.1,<4.1` | 密码哈希与验证 | [passlib](https://passlib.readthedocs.io/) / [pyca/bcrypt](https://github.com/pyca/bcrypt) |
| Pillow | `>=10.4.0` | 照片预览与头像处理 | [python-pillow/Pillow](https://github.com/python-pillow/Pillow) |

推荐运行环境为 Python 3.12、Node.js 24 LTS 与 MySQL 8.4。FFmpeg / FFprobe 用于视频封面生成与时长检测，运行时检查是否可用。

## 设计取舍

- Vue 组件负责页面与交互，Pinia 管理登录状态；当前页面切换由 `App.vue` 管理，没有引入 Vue Router。
- FastAPI 提供类型验证和接口文档，SQLAlchemy 将业务操作与个人操作历史放在同一事务中提交。
- MySQL 使用 utf8mb4，保存成员关系、生活记录、相册、消息、收藏与审计数据。
- 用户与管理员使用不同 Cookie 名称、令牌范围和鉴权入口，支持在同一浏览器同时登录两端。
- 原媒体文件保留上传字节，预览图独立生成；通过成员鉴权接口读取媒体，视频支持 Range 请求。
- 足迹地图读取本地边界与城市索引，搜索时无需外部地图服务；数据来源见 [地图说明](./frontend/user/public/maps/README.md)。
- tsParticles 通过 npm 依赖引入，MIT 许可说明保留在 [tsparticles-LICENSE.txt](./frontend/user/src/assets/tsparticles-LICENSE.txt)。

## 构建与检查

GitHub Actions 使用前端锁文件安装与构建两套应用，并在独立 MySQL 服务上运行后端集成测试。详细操作见 [README](./README.md#测试与自动检查)。
