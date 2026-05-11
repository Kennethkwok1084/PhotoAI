# PhotoAI 开发文档

## 1. 文档说明

本文档面向 PhotoAI 的开发实现，内容包括项目结构、模块职责、数据库设计原则、接口规划、任务队列设计、AI Worker 设计、Android 客户端设计、Web 前端设计、部署方式和开发阶段规划。

PhotoAI 的开发目标是先完成 MVP 闭环，再逐步增强 AI 准确率、多端协同和 NAS 生态兼容能力。

---

## 2. 开发目标

### 2.1 第一阶段目标

第一阶段需要完成以下闭环：

```text
用户登录
→ Android 上传照片
→ 服务端保存原图
→ 生成缩略图
→ Web 时间轴浏览
→ 创建 AI 任务
→ 人脸识别 / OCR
→ 搜索结果展示
```

### 2.2 工程原则

1. 主服务和 AI Worker 解耦；
2. 文件存储和业务逻辑解耦；
3. 手机端 AI 是加速项，不是唯一可信来源；
4. 用户确认结果优先于模型结果；
5. 模型需要版本管理；
6. 所有后台任务必须可重试；
7. 大文件上传必须支持断点续传；
8. 内存占用必须可控；
9. MVP 阶段不强行做复杂共享权限；
10. 数据库结构优先保证清晰和可扩展。

---

## 3. 仓库结构建议

```text
photoai
├── server
│   ├── app
│   │   ├── api
│   │   ├── auth
│   │   ├── users
│   │   ├── assets
│   │   ├── albums
│   │   ├── storage
│   │   ├── upload
│   │   ├── metadata
│   │   ├── thumbnails
│   │   ├── ai
│   │   ├── faces
│   │   ├── ocr
│   │   ├── search
│   │   ├── jobs
│   │   ├── config
│   │   └── common
│   ├── migrations
│   ├── tests
│   ├── pyproject.toml
│   └── main.py
├── workers
│   ├── thumbnail_worker
│   ├── metadata_worker
│   ├── face_worker
│   ├── ocr_worker
│   ├── clip_worker
│   ├── quality_worker
│   └── video_worker
├── web
│   ├── src
│   ├── package.json
│   └── vite.config.ts
├── android
│   ├── app
│   └── build.gradle.kts
├── assistant
│   ├── app
│   └── worker
├── deploy
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── nginx
├── docs
│   ├── mvp.md
│   ├── database.md
│   ├── api.md
│   └── architecture.md
├── .env.example
├── README.md
└── develop.md
```

---

## 4. 后端开发设计

### 4.1 技术选型

| 类型 | 方案 |
|---|---|
| Web 框架 | FastAPI |
| ORM | SQLAlchemy 2.x |
| 数据迁移 | Alembic |
| 数据库 | PostgreSQL 16 |
| 向量扩展 | pgvector |
| 队列 | Redis |
| 异步任务 | Celery 或 Dramatiq |
| 鉴权 | JWT + Refresh Token |
| OIDC | Authlib |
| 文件处理 | pathlib + aiofiles |
| 图片处理 | libvips / Pillow |
| 视频处理 | FFmpeg |

### 4.2 后端模块职责

#### auth 模块

职责：

- 本地账号登录；
- JWT 签发；
- Refresh Token；
- OIDC Provider 配置；
- OIDC 登录回调；
- 当前用户信息；
- 权限中间件。

核心接口：

```text
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh
GET  /api/auth/me
GET  /api/auth/oidc/{provider}/authorize
GET  /api/auth/oidc/{provider}/callback
```

#### users 模块

职责：

- 用户创建；
- 用户资料；
- 用户状态；
- 用户容量统计；
- 用户配置。

核心表：

```text
users
user_auth_identities
user_settings
```

#### storage 模块

职责：

- 管理存储位置；
- 抽象本地/NFS/SMB/外部图库；
- 生成用户原图路径；
- 生成缩略图路径；
- 判断只读图库；
- 文件存在性校验。

存储接口建议：

```python
class StorageAdapter:
    def save_file(self, relative_path: str, fileobj) -> str:
        ...

    def open_file(self, relative_path: str):
        ...

    def delete_file(self, relative_path: str) -> None:
        ...

    def exists(self, relative_path: str) -> bool:
        ...

    def get_public_path(self, relative_path: str) -> str:
        ...
```

#### upload 模块

职责：

- 创建上传会话；
- 接收分片；
- 校验分片；
- 合并文件；
- 校验整体 hash；
- 入库 assets；
- 触发缩略图和 AI 任务。

分片上传流程：

```text
create session
→ upload part 0
→ upload part 1
→ ...
→ complete session
→ merge temp file
→ verify hash
→ move to storage
→ create asset
→ enqueue jobs
```

#### assets 模块

职责：

- 照片和视频资产管理；
- 时间轴查询；
- 照片详情；
- 原图访问；
- 缩略图访问；
- 收藏、隐藏、删除；
- 按时间、类型、人物、标签过滤。

查询要点：

- 必须按 owner_user_id 过滤；
- 默认不显示 deleted_at 非空的资源；
- 时间轴按 taken_at 优先，缺失时按 imported_at；
- 大列表必须分页或游标分页。

#### metadata 模块

职责：

- EXIF 解析；
- GPS 解析；
- 拍摄设备解析；
- 图片宽高、方向；
- 视频时长；
- 媒体类型判断。

#### thumbnails 模块

职责：

- 生成 thumbnail；
- 生成 preview；
- 视频封面图；
- 修正 EXIF 方向；
- WebP/AVIF 后续可选。

建议尺寸：

```text
thumbnail: 512px longest side
preview:   2048px longest side
```

#### ai 模块

职责：

- AI 任务创建；
- AI 结果入库；
- 模型注册；
- 结果状态管理；
- 多端结果合并；
- 低置信度待确认。

#### faces 模块

职责：

- 人脸框保存；
- 人脸 embedding 保存；
- 人物聚类；
- 人物命名；
- 人物合并；
- 人物拆分；
- 用户确认和拒绝。

#### ocr 模块

职责：

- OCR 文本保存；
- OCR 文本块保存；
- OCR 全文索引；
- OCR 结果来源追踪。

#### search 模块

职责：

- 统一搜索入口；
- OCR 文本搜索；
- 标签搜索；
- 人物搜索；
- 时间地点搜索；
- 后期接入语义向量搜索。

---

## 5. 数据库开发规范

### 5.1 ID 策略

所有核心表使用 UUID：

```text
users.id
assets.id
albums.id
ai_tasks.id
faces.id
persons.id
```

原因：

- 客户端可提前生成 ID；
- 适合多端同步；
- 后期支持 Assistant 离线任务；
- 不暴露数据库自增数量。

### 5.2 时间字段

所有时间字段使用 `TIMESTAMPTZ`：

```text
created_at
updated_at
taken_at
imported_at
deleted_at
started_at
finished_at
```

### 5.3 删除策略

MVP 默认使用软删除：

```text
assets.deleted_at
assets.status
```

原图不立即删除，可后续设计回收站清理任务。

### 5.4 多用户隔离

所有用户相关表必须包含：

```text
owner_user_id
user_id
```

查询时必须通过当前用户过滤。不要只依赖前端隐藏。

### 5.5 AI 结果可追溯

AI 结果必须保存：

```text
engine
model_name
model_version
source
device_id
compute_node_id
confidence
status
```

这样后续模型升级和错误回滚才可控。

---

## 6. API 设计规范

### 6.1 统一响应格式

成功响应：

```json
{
  "success": true,
  "data": {},
  "request_id": "req_xxx"
}
```

失败响应：

```json
{
  "success": false,
  "error": {
    "code": "ASSET_NOT_FOUND",
    "message": "照片不存在或无权访问"
  },
  "request_id": "req_xxx"
}
```

### 6.2 分页格式

建议使用游标分页：

```json
{
  "items": [],
  "next_cursor": "cursor_xxx",
  "has_more": true
}
```

时间轴接口示例：

```text
GET /api/assets?cursor=&limit=100&type=photo
```

### 6.3 认证方式

HTTP Header：

```text
Authorization: Bearer <access_token>
```

Refresh Token 可存储在安全 Cookie 或客户端安全存储中。

---

## 7. AI Worker 设计

### 7.1 Worker 类型

| Worker | 职责 |
|---|---|
| thumbnail-worker | 缩略图、预览图、视频封面 |
| metadata-worker | EXIF、GPS、媒体元数据 |
| face-worker | 人脸检测、人脸 embedding |
| ocr-worker | OCR 文字识别 |
| clip-worker | 语义向量 |
| quality-worker | 模糊、重复、质量评分 |
| video-worker | 视频抽帧、基础转码 |

### 7.2 Worker 运行方式

每个 Worker 独立进程运行：

```bash
python -m workers.face_worker
python -m workers.ocr_worker
python -m workers.thumbnail_worker
```

通过环境变量控制：

```env
PHOTOAI_WORKER_TYPE=face
PHOTOAI_WORKER_CONCURRENCY=1
PHOTOAI_MODEL_PROFILE=standard
PHOTOAI_IDLE_UNLOAD_SECONDS=600
```

### 7.3 模型加载策略

模型不能在系统启动时全部加载。

推荐策略：

```text
收到任务
→ 判断模型是否已加载
→ 未加载则加载模型
→ 执行推理
→ 更新最后使用时间
→ 空闲超过阈值释放模型
```

### 7.4 AI 任务状态

```text
pending       等待处理
assigned      已被节点领取
processing    正在处理
completed     处理完成
failed        处理失败
cancelled     已取消
```

### 7.5 结果可信度策略

```text
高置信度：accepted
中置信度：need_review
低置信度：rejected 或仅保存不展示
用户确认：user_confirmed
```

用户确认结果优先级最高，后续模型不能直接覆盖。

---

## 8. 人脸识别开发设计

### 8.1 流程

```text
读取图片/预览图
→ 人脸检测
→ 人脸质量评分
→ 人脸对齐
→ 提取 embedding
→ 保存 faces
→ 聚类生成 persons
→ Web 展示人物相册
```

### 8.2 聚类策略

MVP 可先使用 DBSCAN / HDBSCAN。

基本策略：

- 高相似度自动归类；
- 中等相似度进入待确认；
- 低质量人脸不参与自动合并；
- 用户可手动合并人物；
- 用户可从人物中移除错误人脸。

### 8.3 人脸质量评分

需要考虑：

- 人脸尺寸；
- 模糊程度；
- 遮挡；
- 侧脸角度；
- 光照；
- 检测置信度。

低质量人脸可以保存，但不作为人物代表样本。

---

## 9. OCR 开发设计

### 9.1 OCR 输入判断

不是每张照片都必须 OCR。优先 OCR：

- 截图；
- 文档；
- 票据；
- 证件；
- 海报；
- PPT；
- 聊天记录；
- 含大面积文字的图片。

判断方式：

```text
客户端上报类型
图片宽高比例
文件来源相册
简单文字区域检测
用户手动触发
```

### 9.2 OCR 结果保存

OCR 结果保存到：

```text
ocr_results.full_text
ocr_results.blocks
search_documents.ocr_text
```

### 9.3 搜索策略

MVP 可以先用 PostgreSQL 全文索引：

```sql
to_tsvector('simple', full_text)
```

中文分词后续可增强，比如接入 jieba、pg_jieba 或应用层分词。

---

## 10. Android 客户端开发设计

### 10.1 核心模块

| 模块 | 作用 |
|---|---|
| auth | 登录和 Token 管理 |
| media | 扫描 MediaStore |
| backup | 自动备份和上传 |
| local_db | 本地备份状态 |
| ai_local | 本地 OCR、人脸检测、分类 |
| sync | 与服务端同步 |
| gallery | 本地/远程照片展示 |
| settings | 备份和 AI 策略 |

### 10.2 本地状态表

Android 本地建议使用 Room 保存：

```text
local_assets
├── local_id
├── media_store_id
├── uri
├── filename
├── file_size
├── mime_type
├── taken_at
├── hash
├── backup_status
├── server_asset_id
├── last_error
├── updated_at
```

### 10.3 备份状态

```text
pending
hashing
uploading
uploaded
failed
skipped
```

### 10.4 后台策略

使用 WorkManager：

- Wi-Fi 约束；
- 充电约束；
- 电量不低；
- 失败退避重试；
- 用户手动立即备份时可启动 Foreground Service。

### 10.5 端侧 AI

端侧 AI 只作为加速项：

- OCR；
- 人脸检测；
- 基础分类；
- 缩略图；
- 图片质量初筛。

端侧结果必须带上：

```text
engine
model_name
model_version
device_id
confidence
source=mobile
```

---

## 11. Web 前端开发设计

### 11.1 页面规划

| 页面 | 功能 |
|---|---|
| 登录页 | 本地登录、OIDC 登录 |
| 时间轴 | 按日期浏览照片 |
| 照片详情 | 原图、EXIF、AI 标签、OCR 文本 |
| 人物页 | 人物列表、人物命名 |
| 人物详情 | 某个人的所有照片 |
| 搜索页 | 关键词、OCR、人脸、标签搜索 |
| 相册页 | 手动相册 |
| 上传/备份状态页 | 展示设备备份状态 |
| 管理页 | 存储、任务、模型、系统设置 |

### 11.2 性能要求

- 时间轴必须使用虚拟滚动；
- 缩略图懒加载；
- 原图只在详情页加载；
- 大列表使用游标分页；
- 图片组件需要处理加载失败和占位图；
- 视频封面优先展示，不自动加载完整视频。

---

## 12. Desktop Assistant 设计

### 12.1 定位

Assistant 是可选算力节点，不是 MVP 必需项。

用途：

- 高精度模型推理；
- 大批量历史照片处理；
- 使用电脑 CPU/GPU/NPU；
- 减轻服务器压力。

### 12.2 节点注册

Assistant 启动后向服务端注册：

```json
{
  "node_name": "Gaming-PC",
  "node_type": "assistant",
  "platform": "windows-x64",
  "capabilities": {
    "cpu": "Intel i7",
    "gpu": "RTX 4070",
    "memory_gb": 32,
    "tasks": ["face_embed", "ocr", "clip_embed", "video_extract"]
  }
}
```

### 12.3 任务领取

```text
heartbeat
→ claim-task
→ download input
→ run inference
→ submit-result
→ update task status
```

### 12.4 安全原则

- Assistant 只处理当前用户授权任务；
- 不直接拥有数据库权限；
- 通过 API 获取临时文件访问地址；
- 结果回传需要签名或 Token；
- 可限制只在局域网内工作。

---

## 13. 部署设计

### 13.1 基础服务

MVP 需要：

```text
postgres
redis
photoai-server
photoai-worker
photoai-web
```

### 13.2 推荐目录

```text
/opt/photoai
├── docker-compose.yml
├── .env
├── data
│   ├── postgres
│   ├── photoai
│   │   ├── originals
│   │   ├── thumbnails
│   │   ├── previews
│   │   └── cache
│   └── redis
└── logs
```

### 13.3 权限要求

运行容器的用户必须对照片目录拥有读写权限。外部图库可以只读挂载。

```yaml
volumes:
  - /mnt/photos:/data/photoai/originals
  - /mnt/external_photos:/external/photos:ro
```

---

## 14. 配置文件设计

`.env.example` 建议包含：

```env
PHOTOAI_APP_NAME=PhotoAI
PHOTOAI_ENV=production
PHOTOAI_BASE_URL=http://localhost:8080
PHOTOAI_JWT_SECRET=change_this_secret

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=photoai
POSTGRES_USER=photoai
POSTGRES_PASSWORD=photoai_password

REDIS_URL=redis://redis:6379/0

PHOTOAI_STORAGE_ROOT=/data/photoai
PHOTOAI_ORIGINALS_DIR=/data/photoai/originals
PHOTOAI_THUMBNAILS_DIR=/data/photoai/thumbnails
PHOTOAI_PREVIEWS_DIR=/data/photoai/previews
PHOTOAI_CACHE_DIR=/data/photoai/cache

PHOTOAI_ENABLE_OIDC=false
OIDC_PROVIDER_NAME=
OIDC_ISSUER_URL=
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=
OIDC_REDIRECT_URI=

PHOTOAI_ENABLE_LOCAL_AI=true
PHOTOAI_MODEL_PROFILE=standard
PHOTOAI_WORKER_CONCURRENCY=1
PHOTOAI_IDLE_UNLOAD_SECONDS=600

PHOTOAI_MAX_UPLOAD_SIZE_MB=10240
PHOTOAI_CHUNK_SIZE_MB=8
```

---

## 15. 日志与监控

### 15.1 日志内容

必须记录：

- 登录失败；
- 上传失败；
- 文件校验失败；
- AI 任务失败；
- Worker 异常退出；
- 存储路径不可用；
- OIDC 回调失败；
- 数据库迁移失败。

### 15.2 操作日志

重要用户操作写入 `audit_logs`：

```text
删除照片
修改人物名称
合并人物
移除人脸
创建共享相册
修改存储路径
修改 OIDC 配置
```

### 15.3 健康检查

接口：

```text
GET /api/health
GET /api/health/db
GET /api/health/redis
GET /api/health/storage
GET /api/health/workers
```

---

## 16. 测试规划

### 16.1 单元测试

- 用户登录；
- 权限过滤；
- 文件 hash；
- 存储路径生成；
- EXIF 解析；
- AI 结果合并；
- 人物合并和拆分。

### 16.2 集成测试

- 分片上传完整流程；
- 上传中断后恢复；
- 照片入库后生成任务；
- Worker 领取任务并回传；
- OCR 搜索；
- 人物相册查询；
- OIDC 登录回调。

### 16.3 性能测试

测试数据：

```text
1,000 张照片
10,000 张照片
100,000 张照片
```

关注指标：

- 时间轴加载速度；
- 缩略图生成速度；
- 数据库查询耗时；
- AI 任务吞吐；
- 内存占用；
- Worker 失败率。

---

## 17. 开发阶段

### Stage 1：基础后端

- FastAPI 初始化；
- PostgreSQL 连接；
- Alembic 迁移；
- 用户表；
- 登录接口；
- 权限中间件；
- 基础配置。

### Stage 2：上传和资产

- 分片上传；
- 文件合并；
- hash 校验；
- assets 入库；
- asset_files 入库；
- 原图访问接口；
- 缩略图任务创建。

### Stage 3：Web 时间轴

- Web 登录；
- 时间轴接口；
- 缩略图展示；
- 照片详情；
- 收藏和删除；
- 基础搜索。

### Stage 4：Android 备份

- MediaStore 扫描；
- 本地状态数据库；
- 上传队列；
- WorkManager；
- 备份状态 UI；
- 失败重试。

### Stage 5：AI Worker

- ai_tasks；
- Worker 领取任务；
- EXIF 解析；
- 缩略图生成；
- 人脸检测；
- OCR；
- AI 结果入库。

### Stage 6：人物和搜索

- 人脸 embedding；
- 人物聚类；
- 人物命名；
- OCR 全文搜索；
- 标签搜索；
- 搜索聚合页。

### Stage 7：端侧协同

- Android OCR；
- Android 人脸检测；
- AI 结果上传；
- 服务端结果合并；
- 低置信度复核；
- AI 设置页。

### Stage 8：Assistant

- 节点注册；
- 心跳；
- 任务领取；
- 高精度推理；
- 资源限制；
- 桌面 UI。

---

## 18. MVP 完成标准

MVP 完成时，应满足：

1. 可以部署在一台 Linux x86 服务器上；
2. 可以创建用户并登录；
3. 可以通过 Android 自动备份照片；
4. 可以在 Web 上看到时间轴；
5. 可以查看照片详情和 EXIF；
6. 可以生成缩略图；
7. 可以识别人脸并生成初步人物相册；
8. 可以识别 OCR 文本；
9. 可以通过文字搜索找到对应图片；
10. 可以查看 AI 任务状态；
11. 可以限制 Worker 并发和内存占用；
12. 基础服务在 16GB 内存环境下可长期运行。

---

## 19. 后续开发方向

MVP 之后再开发：

- 高级语义搜索；
- 相似照片清理；
- 低质量照片清理；
- 家庭共享相册；
- 地图相册；
- 回忆相册；
- 群晖 Photos 迁移；
- LDAP；
- iOS 客户端；
- GPU 加速；
- 模型管理界面；
- 插件系统。
