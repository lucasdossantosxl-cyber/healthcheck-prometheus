# syntax=docker/dockerfile:1
FROM python:3.12.10-slim-bookworm
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then \
      PIP_CERT=/run/secrets/build_ca pip install --no-cache-dir -r requirements.txt; \
    else pip install --no-cache-dir -r requirements.txt; fi \
    && groupadd --gid 10001 checker \
    && useradd --uid 10001 --gid checker --no-create-home checker
COPY app ./app
COPY config.yaml .
USER 10001:10001
EXPOSE 8000
CMD ["python", "-B", "-u", "-m", "app.checker"]
