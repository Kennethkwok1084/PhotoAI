# PhotoAI Android 执行文档

## 技术路线

目标是性能最高、兼容性最好，因此 MVP 使用传统原生 Android View 体系：

| 类型 | 方案 |
|---|---|
| 语言 | Kotlin |
| UI | XML + ViewBinding |
| 架构 | MVVM |
| 列表 | RecyclerView + ListAdapter / Paging 3 |
| 图片 | Coil 或 Glide，低端机优先验证 Glide |
| 本地库 | Room |
| 后台任务 | WorkManager |
| 前台上传 | Foreground Service |
| 网络 | OkHttp + Retrofit 可选 |
| Token | EncryptedSharedPreferences |
| 权限 | AndroidX Activity Result API |

不使用 Compose 作为 MVP 主 UI。照片宫格、分页、长列表、多选、视频缩略图、低端机滚动性能都优先使用成熟 View 体系。

## 最低兼容

| 项 | 建议 |
|---|---|
| minSdk | 23 |
| targetSdk | 按发布时 Google Play 要求更新 |
| 图片权限 | Android 13+ 使用 READ_MEDIA_IMAGES / READ_MEDIA_VIDEO |
| 旧版权限 | Android 12- 使用 READ_EXTERNAL_STORAGE |
| 后台上传 | WorkManager + 前台通知 |

## 模块结构

```text
android/app/src/main/java/com/photoai/app
├── auth
├── media
├── backup
├── gallery
├── network
├── database
├── settings
├── common
└── MainActivity.kt
```

## 页面

MVP 只做核心页面：

| 页面 | 阶段 | 说明 |
|---|---|---|
| LoginActivity | P0 | 登录 |
| MainActivity | P0 | 主容器 |
| BackupFragment | P0 | 备份状态 |
| LocalPhotosFragment | P0 | 本机照片扫描结果 |
| RemotePhotosFragment | P1 | 已备份照片 |
| PhotoDetailActivity | P1 | 照片详情 |
| SettingsFragment | P1 | 备份策略 |

底部 Tab MVP：

```text
相片
备份
我的
```

后续再扩展到：

```text
首页
相片
时间轴
发现
我的
```

## Room 表

### local_assets

```kotlin
@Entity(
    tableName = "local_assets",
    indices = [
        Index(value = ["mediaStoreId"], unique = true),
        Index(value = ["fileHash"]),
        Index(value = ["backupStatus"])
    ]
)
data class LocalAssetEntity(
    @PrimaryKey val id: String,
    val mediaStoreId: Long,
    val uri: String,
    val filename: String,
    val mimeType: String,
    val fileSize: Long,
    val width: Int?,
    val height: Int?,
    val durationMs: Long?,
    val takenAt: Long?,
    val dateModified: Long?,
    val fileHash: String?,
    val backupStatus: String,
    val serverAssetId: String?,
    val lastError: String?,
    val createdAt: Long,
    val updatedAt: Long
)
```

### upload_tasks

```kotlin
@Entity(
    tableName = "upload_tasks",
    indices = [Index(value = ["status"])]
)
data class UploadTaskEntity(
    @PrimaryKey val id: String,
    val localAssetId: String,
    val sessionId: String?,
    val status: String,
    val uploadedBytes: Long,
    val totalBytes: Long,
    val retryCount: Int,
    val nextRetryAt: Long?,
    val lastError: String?,
    val createdAt: Long,
    val updatedAt: Long
)
```

## 备份状态

```text
pending
hashing
checking
uploading
uploaded
failed
skipped
```

## MediaStore 扫描

扫描字段：

```text
_ID
DISPLAY_NAME
MIME_TYPE
SIZE
WIDTH
HEIGHT
DURATION
DATE_TAKEN
DATE_MODIFIED
RELATIVE_PATH
```

扫描流程：

```text
检查权限
→ 查询 Images
→ 查询 Video
→ upsert local_assets
→ 标记本地已删除文件
→ 生成待备份任务
```

## Hash 策略

MVP 使用 SHA-256。

为减少耗电：

1. 只对待上传文件计算 hash。
2. 文件大小和修改时间未变化时复用旧 hash。
3. 充电且 Wi-Fi 时优先批量 hash。
4. 手动立即备份时可边 hash 边上传。

## 上传策略

默认：

| 项 | 值 |
|---|---|
| chunk size | 8MB |
| 并发文件数 | 1 |
| 单文件分片并发 | 1 |
| 重试次数 | 3 |
| 退避 | 30s、2min、10min |

低端机优先稳定，不做激进并发。

流程：

```text
读取 local_assets pending
→ hash
→ POST /assets/check
→ 已存在则标记 uploaded
→ POST /uploads/sessions
→ PUT parts
→ POST complete
→ 保存 serverAssetId
```

## 后台策略

WorkManager 约束：

```text
NetworkType.UNMETERED 默认
requiresBatteryNotLow = true
requiresCharging 用户可选
```

用户点击“立即备份”：

```text
启动 Foreground Service
显示通知和进度
允许移动网络取决于用户设置
```

## UI 要求

### 备份页

必须显示：

```text
已备份数量
待备份数量
失败数量
当前上传文件
上传速度
暂停 / 继续
立即备份
```

### 相片页

列表要求：

1. RecyclerView GridLayoutManager。
2. 一行 3 或 4 列。
3. 缩略图固定宽高，避免滚动抖动。
4. 视频显示播放角标。
5. 支持分页加载。
6. 图片加载必须有占位和失败图。

### 详情页

必须支持：

1. 单张大图预览。
2. 双指缩放可后续做，MVP 可先完整显示。
3. 显示文件名、拍摄时间、大小、分辨率。
4. 收藏和删除操作。

## Android P0 TODO

1. 建立 Android 项目。
2. 配置 Kotlin、ViewBinding、Room、WorkManager、OkHttp。
3. 实现登录页。
4. 实现 Token 保存和自动刷新。
5. 实现相册权限申请。
6. 实现 MediaStore 扫描。
7. 实现 Room local_assets。
8. 实现备份任务表。
9. 实现上传 API 客户端。
10. 实现 WorkManager 备份。
11. 实现备份状态页。

## Android 验收

1. Android 8 及以上设备可正常运行。
2. Android 13+ 权限申请正确。
3. 可扫描图片和视频。
4. 可上传至少 1000 张照片。
5. 断网后不会丢任务。
6. 重启 App 后备份状态正确。
7. 长列表滚动不卡顿。
8. 后台备份有系统通知。

