#!/usr/bin/env bash
# First-time install / update on Ubuntu 24.04. Run as root from anywhere: bash deploy/setup.sh
set -euo pipefail
apt-get install -yqq python3-venv git >/dev/null
id berlari >/dev/null 2>&1 || useradd --system --home /opt/berlari --shell /usr/sbin/nologin berlari
if [ -d /opt/berlari/.git ]; then git -C /opt/berlari pull -q; else git clone -q https://github.com/juanjosua/berlari.git /opt/berlari; fi
mkdir -p /var/lib/berlari && chown berlari: /var/lib/berlari
[ -d /opt/berlari/.venv ] || python3 -m venv /opt/berlari/.venv
/opt/berlari/.venv/bin/pip install -q -r /opt/berlari/requirements.txt
if [ ! -f /opt/berlari/.env ]; then
  cp /opt/berlari/.env.example /opt/berlari/.env
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')|" /opt/berlari/.env
  echo "Created /opt/berlari/.env - fill in STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, BASE_URL"
fi
chown root:berlari /opt/berlari/.env && chmod 640 /opt/berlari/.env
cp /opt/berlari/deploy/berlari.service /opt/berlari/deploy/berlari-nightly.service /opt/berlari/deploy/berlari-nightly.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable -q berlari && systemctl restart berlari
systemctl enable -q --now berlari-nightly.timer
echo "Berlari running on 127.0.0.1:8000"
