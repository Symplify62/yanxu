#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" = 0
test -f /etc/letsencrypt/live/test-yanxu.qjl666.xyz/fullchain.pem
test -f /etc/letsencrypt/live/test-yanxu.qjl666.xyz/privkey.pem
release="$(readlink -f /opt/yanxu-test/current)"
case "$release" in /opt/yanxu-test/releases/*) ;; *) exit 1;; esac
install -m 644 "$release/deploy/testing/nginx-https.conf" /etc/nginx/sites-available/yanxu-test
nginx -t
systemctl reload nginx
curl -fsS --retry 8 --retry-delay 1 https://test-yanxu.qjl666.xyz/api/health
