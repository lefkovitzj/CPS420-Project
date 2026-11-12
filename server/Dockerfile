FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 5000

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port \"$PORT\""]
