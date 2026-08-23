# ---- builder: build the wheel ----
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir hatchling \
    && python -m hatchling build -t wheel

# ---- runtime: slim, non-root, plancritic on PATH ----
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /opt/plancritic
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir "/tmp/planner_critic-0.2.1-py3-none-any.whl[server]" && rm -f /tmp/*.whl \
    && mkdir -p /data && chmod 777 /data
USER nobody
ENTRYPOINT ["plancritic"]
CMD ["--version"]
