#!/usr/bin/env bash

set -euo pipefail

echo "== Host =="
hostnamectl || true

echo
echo "== Uptime / Load =="
uptime

echo
echo "== Memory =="
free -h

echo
echo "== Disk =="
df -h /

echo
echo "== Top memory consumers =="
ps aux --sort=-%mem | head -n 15

echo
echo "== Top CPU consumers =="
ps aux --sort=-%cpu | head -n 15

echo
echo "== systemd services (running) =="
systemctl list-units --type=service --state=running --no-pager | head -n 80

echo
echo "== Listening ports =="
ss -lntup || true

echo
echo "== Docker containers =="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true

echo
echo "== Python / Node / Postgres processes =="
ps aux | grep -E 'python|node|postgres|gunicorn|uvicorn|pm2' | grep -v grep || true

echo
echo "== PostgreSQL version =="
psql --version 2>/dev/null || true

echo
echo "== Recommendations =="
echo "1. Check free RAM after subtracting cache pressure and active services."
echo "2. If available RAM under steady load is below ~300 MB, do not start the third project yet."
echo "3. If swap is absent on a 1 GB VPS, add swap before production rollout."