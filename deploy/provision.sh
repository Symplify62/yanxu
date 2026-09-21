#!/usr/bin/env bash
set -euo pipefail
umask 022
# Run as root after placing the release in /opt/yanxu/releases/<name>.
release="${1:?absolute release directory required}"
test "$(id -u)" = 0
test -f "$release/backend/uv.lock"
test -f /opt/yanxu-transfer/server.env
id yanxu >/dev/null 2>&1 || useradd --system --home /var/lib/yanxu --shell /usr/sbin/nologin yanxu
install -d -o yanxu -g yanxu -m 750 /var/lib/yanxu/data /var/lib/yanxu/artifacts
install -m 600 /opt/yanxu-transfer/server.env /etc/yanxu.env
export UV_PYTHON_INSTALL_DIR=/opt/yanxu-python
/opt/yanxu-tools/uv python install 3.13
cd "$release/backend"
if test -d "$release/deploy/wheels"; then
  /opt/yanxu-tools/uv venv --python 3.13
  /opt/yanxu-tools/uv pip sync --python .venv/bin/python --no-index --find-links "$release/deploy/wheels" --require-hashes "$release/deploy/requirements.txt"
else
  /opt/yanxu-tools/uv sync --frozen --no-dev --python 3.13
fi
chmod -R o+rX /opt/yanxu-python
chmod 755 /opt/yanxu /opt/yanxu/releases
chmod -R a+rX "$release"
ln -sfn "$release" /opt/yanxu/current
install -o yanxu -g yanxu -m 644 "$release/deploy/yanxu-debug.apk" /var/lib/yanxu/artifacts/yanxu-debug.apk
for unit in api analysis cloud; do
  case "$unit" in
    api) args='uvicorn yanxu.api:create_app --factory --host 127.0.0.1 --port 5189 --proxy-headers --forwarded-allow-ips=127.0.0.1' ;;
    analysis) args='yanxu.worker' ;;
    cloud) args='yanxu.cloud_worker run' ;;
  esac
  cat > "/etc/systemd/system/yanxu-$unit.service" <<EOF
[Unit]
Description=Yanxu $unit
After=network-online.target
Wants=network-online.target
[Service]
User=yanxu
Group=yanxu
WorkingDirectory=/opt/yanxu/current/backend
EnvironmentFile=/etc/yanxu.env
ExecStart=/opt/yanxu/current/backend/.venv/bin/python -m $args
Restart=always
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/yanxu
[Install]
WantedBy=multi-user.target
EOF
done
cat > /etc/systemd/system/yanxu-maintenance.service <<'EOF'
[Unit]
Description=Yanxu database backup and cache cleanup
[Service]
Type=oneshot
User=yanxu
Group=yanxu
WorkingDirectory=/opt/yanxu/current/backend
EnvironmentFile=/etc/yanxu.env
ExecStart=/opt/yanxu/current/backend/.venv/bin/python -m yanxu.maintenance
UMask=0077
EOF
cat > /etc/systemd/system/yanxu-maintenance.timer <<'EOF'
[Unit]
Description=Daily Yanxu maintenance
[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true
[Install]
WantedBy=timers.target
EOF
install -d -m 755 /var/www/yanxu/.well-known/acme-challenge
install -m 644 "$release/deploy/nginx-rates.conf" /etc/nginx/conf.d/yanxu-rates.conf
install -m 644 "$release/deploy/nginx-http.conf" /etc/nginx/sites-available/yanxu
ln -sfn /etc/nginx/sites-available/yanxu /etc/nginx/sites-enabled/yanxu
nginx -t
systemctl daemon-reload
systemctl enable --now yanxu-api yanxu-analysis yanxu-cloud yanxu-maintenance.timer
systemctl restart yanxu-api yanxu-analysis yanxu-cloud
systemctl reload nginx
curl -fsS --retry 10 --retry-connrefused --retry-delay 1 http://127.0.0.1:5189/api/health
