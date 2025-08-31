# syntax=docker/dockerfile:1

FROM python:3.11.9-slim

# Avoid .pyc files, ensure unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only the lockfile first so dependency install layer can cache
COPY env/requirements.lock /tmp/requirements.lock

# Install dependencies with BuildKit cache (fast rebuilds, small image)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements.lock

# Now copy the rest of the project
COPY . /app

# Default command: baseline, calibrated, zero sleep, append to summary
CMD ["python","src/stream.py","--data","data/synth_tokens.json","--mode","baseline","--sleep_ms","0"]
