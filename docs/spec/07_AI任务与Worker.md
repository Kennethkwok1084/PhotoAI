# PhotoAI AI 任务与 Worker

## 目标

MVP 阶段 AI 不追求一次到位，而是先建立可扩展、可重试、可追溯的任务框架。

## Worker 类型

| Worker | 阶段 | 职责 |
|---|---|---|
| thumbnail-worker | P1 | thumbnail、preview、视频封面 |
| metadata-worker | P1 | EXIF、GPS、宽高、视频时长 |
| ocr-worker | P2 | OCR 文字识别 |
| face-worker | P2 | 人脸检测、embedding |
| clip-worker | P3 | 语义向量 |
| quality-worker | P3 | 模糊、重复、质量评分 |

## 任务状态

```text
pending
assigned
processing
completed
failed
cancelled
```

## 任务类型

```text
thumbnail
metadata
face_detect
face_embed
face_cluster
ocr
clip_embed
label
quality
video_extract
```

## 调度流程

```text
asset created
→ create thumbnail task
→ create metadata task
→ worker claim
→ worker process
→ worker complete / fail
→ update asset_files / metadata / ai_results
→ update assets.ai_status
```

## Worker 运行方式

```bash
python -m workers.thumbnail_worker
python -m workers.metadata_worker
python -m workers.ocr_worker
python -m workers.face_worker
```

环境变量：

```env
PHOTOAI_WORKER_TYPE=thumbnail
PHOTOAI_WORKER_CONCURRENCY=1
PHOTOAI_MODEL_PROFILE=standard
PHOTOAI_IDLE_UNLOAD_SECONDS=600
```

## 模型加载策略

```text
收到任务
→ 判断模型是否已加载
→ 未加载则加载
→ 执行推理
→ 更新最后使用时间
→ 空闲超过阈值释放
```

不要在 Worker 启动时加载全部模型。

## 缩略图任务

输入：

```json
{
  "asset_id": "uuid",
  "original_file_id": "uuid",
  "relative_path": "originals/user/2026/05/asset.jpg"
}
```

输出：

```json
{
  "thumbnail": {
    "relative_path": "thumbnails/user/2026/05/asset.webp",
    "width": 512,
    "height": 384
  },
  "preview": {
    "relative_path": "previews/user/2026/05/asset.webp",
    "width": 2048,
    "height": 1536
  }
}
```

尺寸：

```text
thumbnail: longest side 512px
preview: longest side 2048px
```

## Metadata 任务

保存到 `asset_metadata` 和 `assets` 的宽高、时长、拍摄时间字段。

优先级：

1. EXIF `DateTimeOriginal`
2. MediaStore 上报 `taken_at`
3. 文件修改时间
4. 上传时间

## OCR 任务

优先 OCR：

1. 截图。
2. 文档。
3. 票据。
4. 证件。
5. 聊天记录。
6. 用户手动触发。

MVP 可先对截图和用户手动触发图片执行 OCR，避免全图库高成本扫描。

结果保存：

```text
ocr_results.full_text
ocr_results.blocks
ai_results.result_json
```

## Face 任务

流程：

```text
读取 preview
→ 检测人脸框
→ 保存 faces
→ 可选提取 embedding
→ 后续聚类 persons
```

MVP 可以先完成检测和入库，人物聚类作为 P2 后段。

## 结果可信度

| 状态 | 含义 |
|---|---|
| pending | 待确认 |
| accepted | 系统接受 |
| need_review | 需要用户确认 |
| rejected | 不展示 |
| user_confirmed | 用户确认，最高优先级 |

用户确认结果不能被模型升级直接覆盖。

## Worker 验收

1. Worker 可独立启动。
2. Worker 能领取指定类型任务。
3. 任务成功后状态为 completed。
4. 任务失败后记录 error_message。
5. 超过最大重试次数后不再自动执行。
6. 缩略图生成后 Android 可加载。
7. EXIF 解析后资产详情可显示。

