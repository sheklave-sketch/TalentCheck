#!/bin/bash
# TalentCheck VPS Setup Script
# Run as root on 31.97.47.190
# Usage: bash vps_setup.sh

set -e

echo "=== TalentCheck VPS Setup ==="

# ─── 1. Clone repo ─────────────────────────────────────────────────────────
cd /root
if [ -d "talentcheck" ]; then
  echo "Updating existing clone..."
  cd talentcheck && git pull origin main
else
  echo "Cloning repo..."
  git clone https://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@github.com/sheklave-sketch/TalentCheck.git talentcheck
  cd talentcheck
fi

# ─── 2. Python venv + deps ─────────────────────────────────────────────────
python3 -m venv /root/talentcheck/venv
/root/talentcheck/venv/bin/pip install --upgrade pip -q
/root/talentcheck/venv/bin/pip install -r api/requirements.txt -q
echo "Dependencies installed."

# ─── 3. Write .env ─────────────────────────────────────────────────────────
# EDIT DATABASE_URL with your Supabase postgres password before running
cat > /root/talentcheck/.env << 'ENVEOF'
DATABASE_URL=postgresql+asyncpg://postgres.ysrzmvsrvtovmiqtokqu:REPLACE_WITH_DB_PASSWORD@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
SECRET_KEY=REDACTED_SECRET_KEY
ALGORITHM=HS256
SUPABASE_URL=https://ysrzmvsrvtovmiqtokqu.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlzcnptdnNydnRvdm1pcXRva3F1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTUwMTQ4NywiZXhwIjoyMDg3MDc3NDg3fQ.zUF-lzsa4SHjZLJ1DJ_1R6C0r1GkpTDMs6pHbk_6Q08
FRONTEND_URL=https://talentcheck.vercel.app
DEBUG=false
ENVEOF
echo ".env written (update DATABASE_URL with real password)"

# ─── 4. systemd service ────────────────────────────────────────────────────
cat > /etc/systemd/system/talentcheck-api.service << 'SVCEOF'
[Unit]
Description=TalentCheck FastAPI
After=network.target

[Service]
User=root
WorkingDirectory=/root/talentcheck
EnvironmentFile=/root/talentcheck/.env
ExecStart=/root/talentcheck/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable talentcheck-api
systemctl restart talentcheck-api
echo "Service started on port 8001."

# ─── 5. Nginx config ───────────────────────────────────────────────────────
# Add /talentcheck location to existing nginx (avoids conflict with wase-bot)
NGINX_CONF="/etc/nginx/sites-available/talentcheck"
cat > "$NGINX_CONF" << 'NGINXEOF'
server {
    listen 80;
    server_name _;

    location /talentcheck/ {
        rewrite ^/talentcheck(/.*)$ $1 break;
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
NGINXEOF

# Only enable if not already linked
if [ ! -L /etc/nginx/sites-enabled/talentcheck ]; then
  ln -s "$NGINX_CONF" /etc/nginx/sites-enabled/talentcheck
fi

nginx -t && systemctl reload nginx
echo "Nginx configured. API reachable at http://31.97.47.190/talentcheck"

echo ""
echo "=== Setup complete ==="
echo "API:  http://31.97.47.190/talentcheck/health"
echo "Docs: http://31.97.47.190/talentcheck/docs"
echo ""
echo "IMPORTANT: Edit /root/talentcheck/.env and replace REPLACE_WITH_DB_PASSWORD"
echo "Then: systemctl restart talentcheck-api"
