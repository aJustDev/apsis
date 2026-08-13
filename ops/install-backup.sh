#!/usr/bin/env bash
# Instala en cartagena el backup diario de apsis: directorio de destino,
# unidad y timer. Idempotente, se puede repetir sin efectos raros.
#
# Se ejecuta EN el VPS y necesita sudo, porque escribe en /srv y en
# /etc/systemd/system:
#
#   ssh -t cartagena 'bash /opt/apsis/ops/install-backup.sh'
#
# Requiere que el repo ya este desplegado en /opt/apsis. Las unidades se
# copian a /etc en vez de enlazarse: el deploy hace `git reset --hard` y un
# enlace al checkout se quedaria a merced de esa rama.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/apsis}"
BACKUP_DIR="${BACKUP_DIR:-/srv/apsis-backups}"
UNIT_DIR=/etc/systemd/system
OWNER="${OWNER:-$(id -un)}"

[ -x "$APP_DIR/ops/backup.sh" ] || { echo "falta $APP_DIR/ops/backup.sh (despliega primero)" >&2; exit 1; }

sudo install -d -o "$OWNER" -g "$OWNER" -m 0750 "$BACKUP_DIR"
sudo install -m0644 "$APP_DIR/ops/systemd/apsis-backup.service" "$UNIT_DIR/apsis-backup.service"
sudo install -m0644 "$APP_DIR/ops/systemd/apsis-backup.timer" "$UNIT_DIR/apsis-backup.timer"
sudo systemctl daemon-reload
sudo systemctl enable --now apsis-backup.timer

echo "--- timer ---"
systemctl list-timers apsis-backup.timer --no-pager | head -3

echo
echo "--- primera ejecucion, para comprobar dump y subida ---"
sudo systemctl start apsis-backup.service || true
journalctl -q -u apsis-backup.service -n 20 --no-pager -o cat
echo
echo "resultado: $(systemctl show apsis-backup.service -p Result --value)"
ls -la "$BACKUP_DIR/daily" 2>/dev/null || true
