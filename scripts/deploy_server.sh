#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/var/www/itcenterstore}"
ENV_FILE="${ENV_FILE:-/etc/itcenterstore.env}"
SERVICE_NAME="${SERVICE_NAME:-itcenterstore}"
BRANCH="${BRANCH:-main}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/itcenterstore}"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script with sudo."
    exit 1
fi

for required_path in \
    "${APP_DIR}/.git" \
    "${APP_DIR}/venv/bin/activate" \
    "${APP_DIR}/manage.py" \
    "${ENV_FILE}"; do
    if [[ ! -e "${required_path}" ]]; then
        echo "Missing required path: ${required_path}"
        exit 1
    fi
done

cd "${APP_DIR}"
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "DATABASE_URL is missing from ${ENV_FILE}."
    exit 1
fi

install -d -m 700 "${BACKUP_DIR}"
timestamp="$(date +%Y%m%d-%H%M%S)"
database_backup="${BACKUP_DIR}/database-before-${timestamp}.dump"

echo "Creating PostgreSQL backup: ${database_backup}"
pg_dump --format=custom --no-owner --no-privileges \
    --file="${database_backup}" "${DATABASE_URL}"

echo "Fetching ${BRANCH} from GitHub..."
git fetch origin "${BRANCH}"
git merge --ff-only "origin/${BRANCH}"

# shellcheck disable=SC1091
source "${APP_DIR}/venv/bin/activate"
python -m pip install --disable-pip-version-check -r requirements.txt
python manage.py check
python manage.py migrate --noinput
python manage.py collectstatic --noinput

chown -R www-data:www-data "${APP_DIR}/staticfiles"
systemctl restart "${SERVICE_NAME}"
nginx -t

systemctl is-active --quiet "${SERVICE_NAME}"
curl --fail --silent --show-error --max-time 20 \
    --resolve itcenterstore.com:443:127.0.0.1 \
    https://itcenterstore.com/ >/dev/null

find "${BACKUP_DIR}" -maxdepth 1 -type f -name 'database-before-*.dump' \
    -printf '%T@ %p\n' | sort -nr | tail -n +11 | cut -d' ' -f2- |
    while IFS= read -r old_backup; do
        rm -f -- "${old_backup}"
    done

echo "Deployment completed successfully."
