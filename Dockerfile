# Pinned base image -- see section 29, avoid floating `latest` for anything
# that affects reproducibility.
FROM python:3.12.8-slim-bookworm

# ffmpeg/ffprobe are required for section 16 (validate + transcode media).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 shortbridge \
    && useradd --uid 1000 --gid shortbridge --shell /bin/bash --create-home shortbridge

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini entrypoint.sh ./
RUN chmod +x entrypoint.sh

RUN mkdir -p /data /media/inbox /media/import /media/processed \
    && chown -R shortbridge:shortbridge /data /media /app

USER shortbridge

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

CMD ["./entrypoint.sh"]
