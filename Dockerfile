FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Install dependencies first so Docker caches this layer until requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
COPY data ./data
COPY scripts ./scripts
COPY start.sh ./start.sh

# Make the startup script executable.
RUN chmod +x start.sh

# Run as a non-root user.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
# Default: simple uvicorn. Render/production overrides with start.sh.
CMD ["./start.sh"]
