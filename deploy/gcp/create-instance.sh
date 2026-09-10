#!/bin/bash
# PayMethodFinder を動かす Compute Engine VM を作成する。
# 事前に `gcloud auth login` と `gcloud config set project <PROJECT_ID>` が
# 済んでいること。ローカルマシンから一度だけ実行する。
#
# 使い方: PROJECT_ID=your-project ./deploy/gcp/create-instance.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?PROJECT_ID を環境変数で指定してください}"
ZONE="${ZONE:-asia-northeast1-a}"
INSTANCE_NAME="${INSTANCE_NAME:-paymethodfinder}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-small}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

gcloud compute firewall-rules describe allow-http --project="$PROJECT_ID" >/dev/null 2>&1 || \
  gcloud compute firewall-rules create allow-http \
    --project="$PROJECT_ID" \
    --allow=tcp:80 \
    --target-tags=http-server \
    --description="Allow HTTP for PayMethodFinder"

gcloud compute instances create "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --tags=http-server \
  --boot-disk-size=20GB \
  --metadata-from-file=startup-script="$SCRIPT_DIR/startup-script.sh"

echo "Instance created. Next: SSH in and create /opt/paymethodfinder/.env.gcp, then run deploy.sh."
