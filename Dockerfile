FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml README.md ./
COPY uv.lock* ./
COPY plane_mcp/ ./plane_mcp/
COPY cloudshift/ ./cloudshift/

RUN uv pip install --system --no-cache .

RUN useradd --create-home --uid 10001 mcp
USER mcp

ENV MCP_HOST=0.0.0.0 \
    MCP_PORT=8211

EXPOSE 8211

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${MCP_PORT}/http/api-key/mcp | grep -qE "^(200|401|405|406)$" || exit 1

ENTRYPOINT ["python", "-m", "plane_mcp"]
CMD ["http"]
