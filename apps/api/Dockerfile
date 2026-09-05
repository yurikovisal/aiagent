FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY meza ./meza
RUN uv venv .venv && uv pip install --python .venv/bin/python -e .
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "meza.app:app", "--host", "0.0.0.0", "--port", "8000"]
