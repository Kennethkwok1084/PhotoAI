# PhotoAI API 接口规范

## 通用规则

Base URL：

```text
/api
```

认证：

```text
Authorization: Bearer <access_token>
```

所有接口返回统一响应：

```json
{
  "success": true,
  "data": {},
  "request_id": "req_123"
}
```

## Auth API

### POST /auth/register

请求：

```json
{
  "username": "admin",
  "email": "admin@example.com",
  "password": "ChangeMe123",
  "display_name": "Admin"
}
```

响应：

```json
{
  "id": "uuid",
  "username": "admin",
  "email": "admin@example.com",
  "display_name": "Admin"
}
```

### POST /auth/login

请求：

```json
{
  "username": "admin",
  "password": "ChangeMe123",
  "device_name": "Xiaomi 14"
}
```

响应：

```json
{
  "access_token": "jwt",
  "refresh_token": "token",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "username": "admin",
    "display_name": "Admin",
    "role": "admin"
  }
}
```

### POST /auth/refresh

请求：

```json
{
  "refresh_token": "token"
}
```

响应同登录。

### GET /auth/me

响应：

```json
{
  "id": "uuid",
  "username": "admin",
  "email": "admin@example.com",
  "display_name": "Admin",
  "role": "admin",
  "used_storage_bytes": 0,
  "storage_quota_bytes": null
}
```

## Upload API

### POST /uploads/sessions

创建上传会话。

请求：

```json
{
  "filename": "IMG_0001.jpg",
  "file_hash": "sha256_hex",
  "file_size": 3456789,
  "mime_type": "image/jpeg",
  "chunk_size": 8388608,
  "device_asset_id": "mediastore_123",
  "taken_at": "2026-05-11T10:00:00+08:00"
}
```

响应：

```json
{
  "session_id": "uuid",
  "status": "uploading",
  "chunk_size": 8388608,
  "total_chunks": 1,
  "uploaded_parts": [],
  "asset_exists": false,
  "asset_id": null
}
```

如果服务端已存在同 hash 资产：

```json
{
  "session_id": null,
  "status": "completed",
  "asset_exists": true,
  "asset_id": "uuid"
}
```

### PUT /uploads/sessions/{session_id}/parts/{part_index}

请求体为二进制分片。

Header：

```text
Content-Type: application/octet-stream
X-Part-Checksum: sha256_hex
```

响应：

```json
{
  "session_id": "uuid",
  "part_index": 0,
  "part_size": 3456789,
  "status": "uploaded"
}
```

### POST /uploads/sessions/{session_id}/complete

请求：

```json
{
  "file_hash": "sha256_hex"
}
```

响应：

```json
{
  "asset_id": "uuid",
  "status": "completed",
  "original_file_id": "uuid"
}
```

### GET /uploads/sessions/{session_id}

响应：

```json
{
  "id": "uuid",
  "filename": "IMG_0001.jpg",
  "file_size": 3456789,
  "chunk_size": 8388608,
  "total_chunks": 1,
  "uploaded_chunks": 1,
  "uploaded_parts": [0],
  "status": "uploading"
}
```

## Asset API

### GET /assets

查询参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| cursor | string | 游标 |
| limit | int | 默认 100，最大 200 |
| type | string | photo / video |
| favorite | bool | 是否收藏 |
| q | string | 简单关键词 |

响应：

```json
{
  "items": [
    {
      "id": "uuid",
      "asset_type": "photo",
      "original_filename": "IMG_0001.jpg",
      "mime_type": "image/jpeg",
      "file_size": 3456789,
      "width": 4000,
      "height": 3000,
      "duration_ms": null,
      "taken_at": "2026-05-11T10:00:00+08:00",
      "imported_at": "2026-05-11T10:01:00+08:00",
      "favorite": false,
      "ai_status": "pending",
      "thumbnail_url": "/api/assets/uuid/thumbnail"
    }
  ],
  "next_cursor": "cursor",
  "has_more": true
}
```

### GET /assets/{asset_id}

响应：

```json
{
  "id": "uuid",
  "asset_type": "photo",
  "original_filename": "IMG_0001.jpg",
  "file_hash": "sha256_hex",
  "mime_type": "image/jpeg",
  "file_size": 3456789,
  "width": 4000,
  "height": 3000,
  "taken_at": "2026-05-11T10:00:00+08:00",
  "favorite": false,
  "metadata": {
    "camera_make": "Xiaomi",
    "camera_model": "Xiaomi 14",
    "gps_latitude": null,
    "gps_longitude": null
  },
  "files": {
    "thumbnail_url": "/api/assets/uuid/thumbnail",
    "preview_url": "/api/assets/uuid/preview",
    "original_url": "/api/assets/uuid/original"
  }
}
```

### 文件接口

```text
GET /assets/{asset_id}/thumbnail
GET /assets/{asset_id}/preview
GET /assets/{asset_id}/original
```

规则：

1. 必须鉴权。
2. 必须验证资产属于当前用户。
3. 原图接口可支持 `Range`，方便视频播放。

### 收藏与删除

```text
POST   /assets/{asset_id}/favorite
DELETE /assets/{asset_id}/favorite
DELETE /assets/{asset_id}
```

`DELETE` 默认软删除。

## AI API

### GET /ai/tasks

查询参数：

```text
status=pending&task_type=ocr&limit=50
```

### POST /ai/tasks/{task_id}/claim

Worker 领取任务。

请求：

```json
{
  "node_id": "uuid",
  "worker_type": "ocr"
}
```

### POST /ai/tasks/{task_id}/complete

请求：

```json
{
  "output": {},
  "results": []
}
```

### POST /ai/tasks/{task_id}/fail

请求：

```json
{
  "error_message": "model load failed"
}
```

## Android 同步 API

### POST /assets/check

Android 上传前批量查询资产是否已存在。

请求：

```json
{
  "items": [
    {
      "device_asset_id": "123",
      "file_hash": "sha256_hex",
      "file_size": 3456789
    }
  ]
}
```

响应：

```json
{
  "items": [
    {
      "device_asset_id": "123",
      "exists": true,
      "asset_id": "uuid"
    }
  ]
}
```

## Search API

```text
GET /search?q=
GET /search/ocr?q=
GET /people
GET /people/{person_id}/assets
```

搜索不是 P0，接口可在 AI 基础完成后实现。

