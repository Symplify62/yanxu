#!/usr/bin/env bash
set -euo pipefail
umask 077

release="${1:?provide an absolute /opt/yanxu-test/releases/<name> directory}"
case "$release" in /opt/yanxu-test/releases/*) ;; *) echo "invalid test release path" >&2; exit 1;; esac
test "$(id -u)" = 0
test -f "$release/backend/uv.lock"
test -f "$release/frontend/dist/account.html"
test -f "$release/config/environments/testing.env"
test -f /etc/yanxu-test.env
test "$(stat -c %a /etc/yanxu-test.env)" = 600
grep -Fx 'YANXU_ENVIRONMENT=testing' "$release/config/environments/testing.env" >/dev/null

id yanxu-test >/dev/null 2>&1 || useradd --system --home /var/lib/yanxu-test --shell /usr/sbin/nologin yanxu-test
install -d -m 755 /opt/yanxu-test /opt/yanxu-test/releases
install -d -o yanxu-test -g yanxu-test -m 750 /var/lib/yanxu-test/data /var/lib/yanxu-test/artifacts
install -d -m 755 /var/www/yanxu-test/.well-known/acme-challenge
chmod 755 /opt/yanxu-test /opt/yanxu-test/releases
chmod -R a+rX "$release"
cd "$release/backend"
export UV_PYTHON_INSTALL_DIR=/opt/yanxu-python
/opt/yanxu-tools/uv python install 3.13
/opt/yanxu-tools/uv sync --frozen --no-dev --python 3.13
chmod -R o+rX /opt/yanxu-python
ln -sfn "$release" /opt/yanxu-test/current

for unit in api analysis cloud; do
  case "$unit" in
    api) args='-m uvicorn yanxu.api:create_app --factory --host 127.0.0.1 --port 5199 --proxy-headers --forwarded-allow-ips=127.0.0.1' ;;
    analysis) args='-m yanxu.worker' ;;
    cloud) args='-m yanxu.cloud_worker run' ;;
  esac
  cat > "/etc/systemd/system/yanxu-test-$unit.service" <<EOF
[Unit]
Description=Yanxu testing $unit
After=network-online.target
Wants=network-online.target
[Service]
User=yanxu-test
Group=yanxu-test
WorkingDirectory=/opt/yanxu-test/current/backend
Environment=YANXU_ENVIRONMENT=testing
EnvironmentFile=/etc/yanxu-test.env
ExecStart=/opt/yanxu-test/current/backend/.venv/bin/python $args
Restart=always
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/yanxu-test
[Install]
WantedBy=multi-user.target
EOF
done
cat > /etc/systemd/system/yanxu-test-maintenance.service <<'EOF'
[Unit]
Description=Yanxu testing backup and cleanup
[Service]
Type=oneshot
User=yanxu-test
Group=yanxu-test
WorkingDirectory=/opt/yanxu-test/current/backend
Environment=YANXU_ENVIRONMENT=testing
EnvironmentFile=/etc/yanxu-test.env
ExecStart=/opt/yanxu-test/current/backend/.venv/bin/python -m yanxu.maintenance
UMask=0077
EOF
cat > /etc/systemd/system/yanxu-test-maintenance.timer <<'EOF'
[Unit]
Description=Daily Yanxu testing maintenance
[Timer]
OnCalendar=*-*-* 04:30:00
Persistent=true
[Install]
WantedBy=timers.target
EOF
install -m 644 "$release/deploy/testing/nginx-rates.conf" /etc/nginx/conf.d/yanxu-test-rates.conf
if test -f /etc/letsencrypt/live/test-yanxu.qjl666.xyz/fullchain.pem; then
  install -m 644 "$release/deploy/testing/nginx-https.conf" /etc/nginx/sites-available/yanxu-test
else
  install -m 644 "$release/deploy/testing/nginx-http.conf" /etc/nginx/sites-available/yanxu-test
fi
ln -sfn /etc/nginx/sites-available/yanxu-test /etc/nginx/sites-enabled/yanxu-test
nginx -t
systemctl daemon-reload
systemctl enable --now yanxu-test-api yanxu-test-analysis yanxu-test-cloud yanxu-test-maintenance.timer
systemctl restart yanxu-test-api yanxu-test-analysis yanxu-test-cloud
systemctl reload nginx
curl -fsS --retry 10 --retry-connrefused --retry-delay 1 http://127.0.0.1:5199/api/health
