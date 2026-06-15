# Image SynthesIA — serveur web + pipeline.
# Cible : Synology DS224+ (x86-64). Base avec uv préinstallé.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# 1) Dépendances d'abord (couche cachée tant que pyproject.toml/uv.lock ne bougent pas).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) Code applicatif.
COPY synthesia/ ./synthesia/
COPY config/ ./config/

# Le venv créé par uv vit dans /app/.venv ; on le met sur le PATH.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Données persistantes (base SQLite + cache du modèle d'embedding) → volume.
VOLUME ["/app/data"]

EXPOSE 8000

# Processus principal = le serveur web (toujours allumé).
# Le pipeline (production du brief) se déclenche via `docker exec` (planificateur DSM).
CMD ["uvicorn", "synthesia.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
