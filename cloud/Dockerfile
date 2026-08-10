# DE: Schlankes Python-Image für Grow Central Cloud.
# EN: Slim Python image for Grow Central Cloud.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# DE/EN: Arbeitsverzeichnis / Working directory.
WORKDIR /app

# DE: Dependencies separat kopieren für Docker-Layer-Cache.
# EN: Copy dependencies separately for Docker layer caching.
COPY cloud/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# DE/EN: Cloud-Quellcode kopieren / Copy cloud source.
COPY cloud /app/cloud
RUN addgroup --system growcentral \
    && adduser --system --ingroup growcentral --home /nonexistent --no-create-home growcentral \
    && mkdir -p /app/cloud/data \
    && chown -R growcentral:growcentral /app/cloud
WORKDIR /app/cloud

# DE: Dokumentierter interner Port.
# EN: Documented internal port.
EXPOSE 8090

USER growcentral

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8090"]
