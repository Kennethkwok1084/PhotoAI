# PhotoAI 产品范围与 MVP

## 产品定位

PhotoAI 是面向家庭服务器、x86 NAS、迷你主机和私有云环境的私有 AI 相册系统。核心目标是让用户把照片保存在自己的设备上，同时获得接近手机厂商相册的备份、浏览、搜索和 AI 整理体验。

## MVP 目标

MVP 必须跑通一条真实可用的闭环：

```text
Android 自动备份
→ Server 私有存储
→ 数据库资产入库
→ 缩略图 / EXIF 处理
→ Android 可浏览已备份照片
→ AI 任务可创建和追踪
→ 人脸 / OCR 基础结果可入库
```

MVP 要证明：

1. Android 可以稳定备份本机照片和视频。
2. 服务端可以安全保存、去重、入库和查询照片。
3. 用户只能访问自己的照片。
4. AI 任务框架可运行，后续模型可替换。
5. 项目结构能持续扩展到 Web、Assistant、更多 AI 能力。

## MVP 必须实现

| 模块 | 功能 | 要求 |
|---|---|---|
| 用户 | 本地账号 | 注册、登录、刷新 Token、退出 |
| 用户 | OIDC | 保留通用 OIDC 结构，MVP 可先只实现配置与回调骨架 |
| 权限 | 用户隔离 | 所有资产、相册、AI 结果按 owner_user_id 过滤 |
| 存储 | 本地目录 | 支持配置 managed library 根目录 |
| 上传 | 分片上传 | 创建会话、上传分片、断点续传、合并、hash 校验 |
| 资产 | 入库 | 保存原图记录、文件记录、基础字段 |
| 媒体 | 缩略图 | 生成 thumbnail 和 preview |
| 媒体 | EXIF | 解析拍摄时间、宽高、方向、设备、GPS |
| Android | 登录 | 本地账号登录、Token 安全保存、自动刷新 |
| Android | 扫描 | 扫描 MediaStore 图片和视频 |
| Android | 备份 | Wi-Fi / 充电策略、失败重试、进度展示 |
| Android | 相片 | 本地与远端照片列表、照片详情 |
| AI | 任务 | ai_tasks 创建、领取、状态更新、失败重试 |
| AI | OCR | 截图/文档类图片 OCR 结果入库 |
| AI | 人脸 | 人脸框和 embedding 字段结构准备，基础检测可运行 |
| 部署 | Docker Compose | postgres、redis、server、worker 可启动 |

## MVP 暂不实现

| 功能 | 原因 |
|---|---|
| iOS 客户端 | 后台能力限制多，先完成 Android |
| Web 完整相册 | 技术栈待定，不阻塞核心备份闭环 |
| 家庭共享权限 | 会显著放大权限模型复杂度 |
| Synology Photos 数据库迁移 | 兼容成本高，后续工具化 |
| 地图相册高级交互 | 需要前端地图和地理聚合 |
| 自动回忆相册 | 依赖更成熟的标签、人物、地点识别 |
| 视频 AI 分析 | 计算成本高，MVP 只做基础封面和播放信息 |
| 插件系统 | 非核心链路 |

## 用户流程

### Android 备份流程

```text
用户登录
→ 授权读取相册
→ 扫描 MediaStore
→ 计算本地文件指纹
→ 查询服务端是否已存在
→ 创建上传会话
→ 分片上传
→ 完成会话
→ 服务端 hash 校验
→ 保存原图
→ 创建 assets / asset_files
→ 创建缩略图、EXIF、AI 任务
→ Android 标记为已备份
```

### 照片查看流程

```text
Android 请求 /api/assets
→ 服务端按 owner_user_id 过滤
→ 返回分页资产列表
→ Android 加载 thumbnail
→ 点击进入详情
→ 请求 preview / original / metadata
```

## 关键状态

### 资产状态

| 状态 | 含义 |
|---|---|
| active | 正常可见 |
| hidden | 隐藏 |
| trashed | 回收站 |
| deleted | 已删除，后台可清理 |

### AI 状态

| 状态 | 含义 |
|---|---|
| pending | 待处理 |
| processing | 处理中 |
| partial | 部分完成 |
| completed | 全部完成 |
| failed | 处理失败 |

### Android 备份状态

| 状态 | 含义 |
|---|---|
| pending | 待备份 |
| hashing | 计算 hash |
| checking | 查询服务端 |
| uploading | 上传中 |
| uploaded | 已备份 |
| failed | 失败 |
| skipped | 跳过 |

## MVP 验收

1. 一台 Linux x86 服务器可通过 Docker Compose 启动基础服务。
2. Android 可登录并保持会话。
3. Android 可扫描至少 1000 张本地照片。
4. Android 可自动上传照片，网络中断后可恢复。
5. 服务端可按用户隔离查询资产。
6. 上传完成后生成原图文件记录和缩略图任务。
7. Worker 可处理缩略图和 EXIF 任务。
8. Android 可看到已备份照片列表和详情。
9. AI 任务失败后可重试。
10. 基础服务在 16GB 内存环境可长期运行。

