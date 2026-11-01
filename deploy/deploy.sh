#!/usr/bin/env bash
# Pull, install, (re)start, and health-check the Plane MCP HTTP server on a Linux host.
#
# Usage:
#   deploy/deploy.sh                 # run as the app user, or via sudo
#   APP_DIR=/srv/plane-mcp deploy/deploy.sh
#
# If a systemd unit named $SERVICE_NAME exists it is restarted; otherwise the server
# is started in the background with nohup. Configuration comes from $APP_DIR/.env.

set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SERVICE_NAME="${SERVICE_NAME:-plane-mcp}"
LOG_DIR="${LOG_DIR:-${APP_DIR}/logs}"
PID_FILE="${APP_DIR}/.plane-mcp.pid"
SKIP_PULL="${SKIP_PULL:-false}"
HEALTH_RETRIES="${HEALTH_RETRIES:-10}"

# The app must never run as root; under sudo, act as the invoking user.
RUN_USER="${RUN_USER:-${SUDO_USER:-$(id -un)}}"
if [ "${RUN_USER}" = "root" ]; then
    echo "Refusing to run the server as root. Set RUN_USER=<user>." >&2
    exit 1
fi
RUN_HOME="$(getent passwd "${RUN_USER}" | cut -d: -f6)"

log() { printf '[%s] [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "$2"; }
die() { log ERROR "$1"; exit 1; }

as_run_user() {
    if [ "$(id -u)" -eq 0 ]; then
        sudo -u "${RUN_USER}" -H bash -c "$1"
    else
        bash -c "$1"
    fi
}

find_uv() {
    local candidate
    for candidate in "${RUN_HOME}/.local/bin/uv" "${RUN_HOME}/.cargo/bin/uv" /usr/local/bin/uv /usr/bin/uv; do
        if [ -x "${candidate}" ]; then
            echo "${candidate}"
            return
        fi
    done
    command -v uv || true
}

load_env() {
    [ -f "${APP_DIR}/.env" ] || die "Missing ${APP_DIR}/.env (copy .env.example and fill it in)"
    set -a
    # shellcheck disable=SC1091
    . "${APP_DIR}/.env"
    set +a
    PORT="${MCP_PORT:-8211}"
    : "${PLANE_API_KEY:?PLANE_API_KEY must be set in .env}"
    : "${PLANE_WORKSPACE_SLUG:?PLANE_WORKSPACE_SLUG must be set in .env}"
}

has_systemd_unit() {
    command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files "${SERVICE_NAME}.service" --no-legend 2>/dev/null | grep -q .
}

pull_code() {
    if [ "${SKIP_PULL}" = "true" ] || [ ! -d "${APP_DIR}/.git" ]; then
        log INFO "Skipping git pull"
        return
    fi
    log INFO "Pulling latest code"
    as_run_user "cd '${APP_DIR}' && git pull --ff-only" || die "git pull failed (local changes or diverged branch?)"
}

install_deps() {
    log INFO "Installing dependencies with ${UV}"
    as_run_user "cd '${APP_DIR}' && '${UV}' sync --frozen --no-dev" || die "uv sync failed"
}

stop_manual_instance() {
    # Only touch this deployment: its recorded PID, then whatever still holds its port.
    if [ -f "${PID_FILE}" ]; then
        kill "$(cat "${PID_FILE}")" 2>/dev/null || true
        rm -f "${PID_FILE}"
    fi
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "${PORT}/tcp" >/dev/null 2>&1 || true
    fi
    sleep 2
}

start_server() {
    mkdir -p "${LOG_DIR}"
    if [ "$(id -u)" -eq 0 ]; then
        chown "${RUN_USER}:" "${LOG_DIR}"
    fi

    if has_systemd_unit; then
        log INFO "Restarting systemd unit ${SERVICE_NAME}"
        if [ "$(id -u)" -eq 0 ]; then
            systemctl restart "${SERVICE_NAME}"
        else
            sudo systemctl restart "${SERVICE_NAME}"
        fi
        return
    fi

    log INFO "No systemd unit '${SERVICE_NAME}'; starting with nohup"
    stop_manual_instance
    local cmd="cd '${APP_DIR}' && set -a && . ./.env && set +a && exec '${APP_DIR}/.venv/bin/plane-mcp-server' http"
    if [ "$(id -u)" -eq 0 ]; then
        nohup sudo -u "${RUN_USER}" -H bash -c "${cmd}" >"${LOG_DIR}/plane-mcp-server.log" 2>&1 &
    else
        nohup bash -c "${cmd}" >"${LOG_DIR}/plane-mcp-server.log" 2>&1 &
    fi
    echo $! >"${PID_FILE}"
    log INFO "Started (PID $!), logs: ${LOG_DIR}/plane-mcp-server.log"
}

health_check() {
    local url="http://127.0.0.1:${PORT}${MCP_PATH_PREFIX:-}/http/api-key/mcp"
    local body='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"deploy-check","version":"0"}}}'
    local code attempt
    for attempt in $(seq 1 "${HEALTH_RETRIES}"); do
        code="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${url}" \
            -H "Authorization: Bearer ${PLANE_API_KEY}" \
            -H "x-workspace-slug: ${PLANE_WORKSPACE_SLUG}" \
            -H 'Content-Type: application/json' \
            -H 'Accept: application/json, text/event-stream' \
            -d "${body}" || true)"
        if [ "${code}" = "200" ]; then
            log OK "Healthy: MCP initialize on ${url} returned 200"
            return
        fi
        log WARN "Not ready (attempt ${attempt}/${HEALTH_RETRIES}, HTTP ${code})"
        sleep 3
    done
    if [ -f "${LOG_DIR}/plane-mcp-server.log" ]; then
        tail -n 20 "${LOG_DIR}/plane-mcp-server.log" >&2
    fi
    die "Server did not become healthy. HTTP 401 means Plane rejected PLANE_API_KEY or the workspace slug."
}

main() {
    [ -d "${APP_DIR}" ] || die "APP_DIR not found: ${APP_DIR}"
    UV="$(find_uv)"
    [ -n "${UV}" ] || die "uv not found for user ${RUN_USER}. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"

    log INFO "Deploying ${APP_DIR} as ${RUN_USER}"
    load_env
    pull_code
    install_deps
    start_server
    health_check
}

main "$@"
