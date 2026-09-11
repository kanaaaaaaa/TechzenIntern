#!/bin/bash
# アプリのコードを Compute Engine VM に同期し、コンテナを再ビルド・再起動する。
# 初回は先に VM 上で /opt/paymethodfinder/.env.gcp を作成しておくこと
# (README.md 参照)。このスクリプトは .env.gcp を上書きしない。
#
# 使い方: PROJECT_ID=your-project ./deploy/gcp/deploy.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?PROJECT_ID を環境変数で指定してください}"
ZONE="${ZONE:-asia-northeast1-a}"
INSTANCE_NAME="${INSTANCE_NAME:-paymethodfinder}"
REMOTE_DIR="/opt/paymethodfinder"
REMOTE_STAGING="paymethodfinder-src-tmp"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Trim frontend/node_modules and other build/runtime artifacts locally before
# upload; the container runs `npm ci` on its own, so sending the local
# node_modules (tens of MB, thousands of files) only slows the deploy down.
STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGE_DIR"' EXIT
cp Dockerfile docker-compose.yml docker-entrypoint.sh .dockerignore "$STAGE_DIR/"
rsync -a --exclude=node_modules --exclude=dist frontend/ "$STAGE_DIR/frontend/"
rsync -a --exclude=db.sqlite3 --exclude=staticfiles --exclude=__pycache__ backend/ "$STAGE_DIR/backend/"

gcloud compute scp --project="$PROJECT_ID" --zone="$ZONE" --tunnel-through-iap --recurse --compress \
  "$STAGE_DIR"/Dockerfile "$STAGE_DIR"/docker-compose.yml "$STAGE_DIR"/docker-entrypoint.sh \
  "$STAGE_DIR"/.dockerignore "$STAGE_DIR"/backend "$STAGE_DIR"/frontend \
  "$INSTANCE_NAME:$REMOTE_STAGING"

gcloud compute ssh --project="$PROJECT_ID" --zone="$ZONE" --tunnel-through-iap "$INSTANCE_NAME" -- "
  set -e
  sudo mkdir -p '$REMOTE_DIR'
  sudo rsync -a --delete \
    --exclude=.env.gcp \
    --exclude=db.sqlite3 --exclude=staticfiles --exclude=dist \
    --exclude=node_modules --exclude=__pycache__ \
    ~/$REMOTE_STAGING/ '$REMOTE_DIR/'
  rm -rf ~/$REMOTE_STAGING
  cd '$REMOTE_DIR'
  sudo docker compose --env-file .env.gcp up -d --build
"
