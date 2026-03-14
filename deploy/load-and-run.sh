#!/usr/bin/env bash
set -euo pipefail

IMAGE_TAR="${1:-}"
APP_ROOT="/opt/multi-rider"
CONF_DIR="${APP_ROOT}/conf"
OUTPUT_DIR="${APP_ROOT}/output"
ENV_FILE="${CONF_DIR}/app.env"
CONTAINER_NAME="${CONTAINER_NAME:-multi-rider}"
HOST_PORT="${HOST_PORT:-5001}"

if [[ -z "${IMAGE_TAR}" ]]; then
  echo "Usage: sudo bash deploy/load-and-run.sh /path/to/multi-rider.tar"
  exit 1
fi

if [[ ! -f "${IMAGE_TAR}" ]]; then
  echo "Image tar not found: ${IMAGE_TAR}"
  exit 1
fi

sudo mkdir -p "${CONF_DIR}" "${OUTPUT_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  sudo cp "$(dirname "$0")/app.env.example" "${ENV_FILE}"
  sudo chmod 600 "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Edit ORACLE_PASSWORD and FLASK_SECRET_KEY first, then rerun."
  exit 0
fi

if sudo grep -Eq '^(ORACLE_PASSWORD=CHANGE_ME|FLASK_SECRET_KEY=CHANGE_ME)' "${ENV_FILE}"; then
  echo "Please update ${ENV_FILE} before starting the container."
  exit 1
fi

LOAD_OUTPUT="$(sudo docker load -i "${IMAGE_TAR}")"
echo "${LOAD_OUTPUT}"

IMAGE_REF="$(printf '%s\n' "${LOAD_OUTPUT}" | awk -F': ' '/Loaded image:/ {print $2; exit}')"
if [[ -z "${IMAGE_REF}" ]]; then
  echo "Unable to find imported multi-rider image."
  exit 1
fi

if sudo docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  sudo docker rm -f "${CONTAINER_NAME}"
fi

sudo docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart unless-stopped \
  -p "${HOST_PORT}:5001" \
  --env-file "${ENV_FILE}" \
  -v "${OUTPUT_DIR}:/app/output:Z" \
  "${IMAGE_REF}"

echo "Container started: ${CONTAINER_NAME}"
echo "URL: http://<host-ip>:${HOST_PORT}/"
echo "Logs: sudo docker logs -f ${CONTAINER_NAME}"
