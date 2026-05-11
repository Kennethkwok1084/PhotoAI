# PhotoAI Server

PhotoAI 后端 P0 服务，使用 FastAPI、SQLAlchemy、Alembic、PostgreSQL 和 Redis。

## Local

```bash
uv sync
uv run alembic upgrade head
uv run photoai-init-storage
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

