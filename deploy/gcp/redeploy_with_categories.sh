#!/bin/bash
# GCP の Compute Engine VM 上で実行するスクリプト。
# 「GitHub main を pull → コンテナを再ビルド → 既存店舗にCSVのカテゴリを反映」
# までを一括で行う。
#
# 前提:
#   - このスクリプトを置いたディレクトリがリポジトリのルート
#     (.env.gcp / docker-compose.yml があり、git clone 済みであること)
#   - 正規化済みの danang_nearby_1000m.csv を、ブラウザSSHの
#     「ファイルをアップロード」機能でホームディレクトリ(~)に
#     アップロード済みであること
#
# 使い方 (VM上のリポジトリルートで): ./deploy/gcp/redeploy_with_categories.sh
#
# 注意: CSVはDockerイメージのビルド時に backend/ ごと COPY されるため、
# 必ず「CSVを配置 → ビルド」の順に実行する必要がある。先にビルドしてから
# CSVを置いても、そのビルドで出来上がったコンテナの中には反映されない。
set -euo pipefail

CSV_SRC="$HOME/danang_nearby_1000m.csv"
CSV_DEST="backend/data/foursquare/danang_nearby_1000m.csv"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> 1/4: git pull origin main"
git pull origin main

echo "==> 2/4: CSVを配置"
if [ ! -f "$CSV_SRC" ]; then
  echo "見つかりません: $CSV_SRC" >&2
  echo "先にブラウザSSHの「ファイルをアップロード」で ~ に置いてください。" >&2
  exit 1
fi
mkdir -p "$(dirname "$CSV_DEST")"
mv "$CSV_SRC" "$CSV_DEST"

echo "==> 3/4: コンテナを再ビルド・再起動 (数分かかります)"
sudo docker compose --env-file .env.gcp up -d --build

echo "==> app コンテナの起動待ち"
for i in $(seq 1 30); do
  if sudo docker compose exec -T app python backend/manage.py check >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "==> 4/4: 既存店舗のカテゴリをCSVから反映"
sudo docker compose exec app python backend/manage.py sync_store_categories_from_csv "$CSV_DEST"

echo "==> 完了"
