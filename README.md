# PayMethodFinder

A web app for searching, registering and updating the payment methods each store accepts.

## Foursquare OS Placesからダナンの店舗を取得

Python 3.9以上の仮想環境で追加依存関係をインストールします。

```powershell
pip install -r backend/requirements-places.txt
```

[Foursquare Places Portal](https://places.foursquare.com/) でアクセストークンを発行し、
PowerShellの現在のセッションだけに設定して実行します。

```powershell
$env:FOURSQUARE_PLACES_TOKEN = "発行したアクセストークン"
python backend/scripts/fetch_danang_places.py
```

または、`.env.example` を `.env` へコピーしてトークンを記入できます。`.env` は
Gitの対象外です。

既定では、ベトナム（`VN`）かつ `locality` または `region` がダナンで、
閉店日が設定されていない場所をIceberg上で絞り込み、最初の10件を
`backend/data/foursquare/danang_places.csv` に保存します。トークンはファイルへ保存しません。

件数、出力形式、閉店済みデータの扱いは変更できます。

```powershell
python backend/scripts/fetch_danang_places.py --limit 100 --output backend/data/foursquare/danang_places.parquet
python backend/scripts/fetch_danang_places.py --limit 10 --include-closed
```

### ANFADA Hotel Danang・Techzenの周辺1kmを取得

次のコマンドは両拠点を囲む範囲をIceberg側で絞り込み、Haversine距離が正確に
1,000m以内となる営業中の場所を件数制限なしで取得します。

```powershell
wsl --cd /mnt/c/Users/ganju/Desktop/PayMethodFinder --exec .venv/bin/python backend/scripts/fetch_nearby_places.py
```

以下の3ファイルが `backend/data/foursquare/` に出力されます。

- `anfada_hotel_danang_1000m.csv`
- `techzen_1000m.csv`
- `danang_nearby_1000m.csv`（上記2ファイルの統合結果）

各行には基準拠点、基準住所、拠点からの距離（`distance_meters`）も含まれます。
半径は、例えば `--radius-meters 500` のように変更できます。

The original static screens are kept in `ScreenPrototype/` for reference; the actual app is built with Vue 3 and Django REST Framework.

## Layout

```text
PayMethodFinder/
├── backend/          Django / Django REST Framework / SQLite
├── frontend/         Vue 3 / Vue Router / Vite / Axios
└── ScreenPrototype/  Initial screen prototypes
```

The backend uses three models.

- `Store`: store name, address, created at, updated at
- `PaymentMethod`: payment method, category, display order, active flag
- `StorePaymentMethod`: a store/payment method pair, its availability and when it was confirmed

Availability has three states: `Accepted`, `Not accepted` and `Unknown`.

## Running on WSL

### 1. Backend

Run from the repository root.

```bash
python3 -m venv .venv  # first time only; .venv is not in the repository
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
export DJANGO_DEBUG=true  # see below; without it the server refuses to start
python manage.py migrate
python manage.py createsuperuser  # only if you want the admin site
python manage.py runserver
```

`DJANGO_SECRET_KEY` and `APP_PASSWORD` have no defaults — a secret with a fallback in
the repository is a secret everyone who can read the repository already has. Production
must supply both, and the server exits with a message naming the missing one. Setting
`DJANGO_DEBUG=true` opts into insecure development stand-ins so local work needs no
setup; `backend/.env.example` lists the variables if you would rather set them properly.

- API: <http://127.0.0.1:8000/api/>
- Admin site: <http://127.0.0.1:8000/admin/>

The first migration seeds four payment methods: Cash, Credit card, E-money and QR code payment. Add more or deactivate them from the Django admin site.

Opening <http://127.0.0.1:8000/> returns 404 until the frontend has been built: the backend
only serves the API and the admin site on its own. Once `frontend/dist/` exists (see
Deploying), Django serves that build at `/` as well — which is a stale copy while you are
working, so use the Vite server below for development.

### 2. Frontend

Run in a separate terminal.

```bash
cd frontend
npm install
npm run dev
```

App: <http://localhost:5173/>

To point the app at a different API, copy `frontend/.env.example` to `frontend/.env` and change `VITE_API_URL`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/stores/?search=...` | Search stores by name and address |
| `POST` | `/api/stores/` | Register a store |
| `GET` | `/api/stores/{id}/` | Store details |
| `PATCH` | `/api/stores/{id}/` | Update a store and its payment statuses |
| `GET` | `/api/payment-methods/` | List active payment methods |
| `POST` | `/api/access/` | Exchange the app password for a token |

Every call except `/api/access/` needs that token in an `Authorization: Bearer <token>` header.

Payment statuses are sent in this shape when registering or updating a store.

```json
{
  "name": "Station Market",
  "address": "1-2-3 Shibuya, Shibuya-ku, Tokyo",
  "payment_statuses": [
    { "payment_method_id": 1, "status": "accepted" },
    { "payment_method_id": 5, "status": "unknown" }
  ]
}
```

## Checks

```bash
cd backend
../.venv/bin/python manage.py test
../.venv/bin/python manage.py makemigrations --check --dry-run

cd ../frontend
npm run build
```

## 変更の反映を確認する

編集した場所によって、反映のされ方と確認方法が変わります。

### フロントエンド（`.vue` / `.js` / `.css`）

```bash
cd frontend
npm run dev
```

<http://localhost:5173/> を開いたまま保存すると、Vite が自動でブラウザに反映します（リロード不要）。
別のターミナルでバックエンドの `runserver` も起動しておいてください。

**開発中に <http://127.0.0.1:8000/> を見ないでください。** `frontend/dist/` がある場合、8000番でも
画面は表示されますが、それは最後にビルドした時点の古いコピーです。編集内容は反映されません。

### バックエンド（`.py`）

`runserver` はファイルの保存を検知して自動的に再起動します（起動ログの `StatReloader` がその印です）。
ただし次のものは自動では反映されません。

| 編集した対象 | 必要な操作 |
| --- | --- |
| `models.py` のフィールドや制約 | `python manage.py makemigrations` のあと `migrate` |
| 環境変数（`APP_PASSWORD` など） | サーバーを Ctrl+C で停止して再起動。環境変数は起動時にしか読まれません |
| `requirements.txt` | `pip install -r backend/requirements.txt` |

### 動作確認のコマンド

```bash
cd backend
../.venv/bin/python manage.py test
../.venv/bin/python manage.py makemigrations --check --dry-run

cd ../frontend
npm run build
```

API を直接確認するときは、アプリのパスワードでトークンを取得してから呼びます。

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/access/ \
  -H 'Content-Type: application/json' -d "{\"password\":\"$APP_PASSWORD\"}" \
  | grep -o '"token":"[^"]*' | cut -d'"' -f4)
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/stores/
```

### 本番（Docker / Render）

開発サーバーと違い、編集しただけでは反映されません。イメージの再ビルドが必要です。
Render の場合は GitHub に push すると自動で再ビルドされますが、**そのたびにデータベースは空に戻ります**。

```bash
docker build -t paymethodfinder .
```

### つまずきやすい点

- **画面が変わらない**: 5173 ではなく 8000 を見ていないか確認してください。それでも変わらなければ
  `Ctrl+Shift+R` でキャッシュを無視して再読み込みします。
- **パスワードを変えたのに再入力を求められない**: 正常な動作です。発行済みのトークンは `APP_PASSWORD`
  ではなく `DJANGO_SECRET_KEY` で署名されているため、パスワードを変えても有効なままです。確認したい
  ときは画面右上の Lock ボタンを押すか、プライベートウィンドウで開いてください。全員のトークンを
  無効にしたい場合は `DJANGO_SECRET_KEY` を変更します。
- **管理画面の CSS が消えた**: `DEBUG=false` で `collectstatic` をせずに起動した場合です。開発時は
  `DJANGO_DEBUG=true` を設定して起動してください。
- **`ImproperlyConfigured` で起動しない**: `DJANGO_SECRET_KEY` か `APP_PASSWORD` が未設定です。
  既定値は意図的に用意していません（リポジトリに書いた秘密は秘密ではないため）。開発中は
  `export DJANGO_DEBUG=true` で開発用の値が使われます。本番では両方を必ず設定してください。
- **パスワードを何度か間違えたら 429 が返る**: 仕様です。共有パスワードは 1 つしかなく総当たりの
  標的になるため、`/api/access/` は IP あたり既定で 1 時間 10 回までに制限しています。回数は
  `APP_ACCESS_THROTTLE_RATE` で変更できます。

## Deploying

The whole app ships as one service: the `Dockerfile` builds the Vue app, then Django serves
it together with the API and the admin site from a single origin. `render.yaml` describes
that service for [Render](https://render.com), but the image runs anywhere Docker does.

```bash
docker build -t paymethodfinder .
docker run -p 8000:8000 -e DJANGO_SECRET_KEY=... -e DJANGO_ALLOWED_HOSTS=localhost paymethodfinder
```

On Render: push the repository to GitHub, choose *New > Blueprint*, and point it at
`render.yaml`. `DJANGO_SECRET_KEY` is generated for you.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | **Required.** Any long random string. No default; the server will not start without it |
| `APP_PASSWORD` | **Required.** The password visitors type to open the app. No default |
| `DJANGO_DEBUG` | Defaults to `false`. Set `true` only for local development |
| `DJANGO_ALLOWED_HOSTS` | Comma separated hostnames. Render's own hostname is added automatically |
| `CSRF_TRUSTED_ORIGINS` | Comma separated `https://…` origins, needed to log into the admin site |
| `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` | Optional. Recreates the admin account on every deploy |
| `APP_ACCESS_THROTTLE_RATE` | Guesses allowed per client IP against the app password. Defaults to `10/hour` |
| `DJANGO_NUM_PROXIES` | Proxies in front of the service, used to identify the client for throttling. `1` on Render, `0` with nothing in front |
| `DATABASE_URL` | Optional. Set it to a `postgres://…` URL to move off SQLite |
| `CORS_ALLOWED_ORIGINS` | Only needed if the frontend is hosted separately |

Two things to keep in mind.

- **The database is disposable.** SQLite lives inside the container, so every deploy or
  restart starts from an empty database with the four payment methods seeded again. Set
  `DATABASE_URL` to a PostgreSQL instance when the data needs to survive.
- **The app is behind a shared password.** Set `APP_PASSWORD` in the Render dashboard before
  the first deploy; there is no default, so the service will not start until you do. Visitors
  enter it once and the browser keeps the token it gets back. Everyone who knows the password
  can create, edit and delete stores; there are no individual accounts yet. Guesses are capped
  at `APP_ACCESS_THROTTLE_RATE` per client IP, counted in memory per worker — with the default
  two workers, an attacker gets roughly twice the stated rate. Give the app a real random
  password rather than relying on the cap alone.

## Google Cloud (Compute Engine)

An alternative to Render: one Compute Engine VM runs both the app container (built from
the same `Dockerfile`) and a PostgreSQL container, wired together by `docker-compose.yml`.
Unlike the SQLite setup above, the database here persists across deploys and restarts in
a named Docker volume.

Prerequisites: the [gcloud CLI](https://cloud.google.com/sdk/docs/install), authenticated
(`gcloud auth login`) with a project selected (`gcloud config set project <PROJECT_ID>`).

### First-time setup

```bash
PROJECT_ID=your-project ./deploy/gcp/create-instance.sh
```

This opens TCP:80 and creates a Debian VM whose startup-script installs Docker. Then, once
the instance is up:

```bash
PROJECT_ID=your-project gcloud compute ssh paymethodfinder -- \
  'sudo mkdir -p /opt/paymethodfinder'
PROJECT_ID=your-project gcloud compute scp .env.gcp.example \
  paymethodfinder:/tmp/.env.gcp
PROJECT_ID=your-project gcloud compute ssh paymethodfinder -- \
  'sudo mv /tmp/.env.gcp /opt/paymethodfinder/.env.gcp'
```

SSH in and edit `/opt/paymethodfinder/.env.gcp` (`sudo nano ...`) with real values —
see the comments in `.env.gcp.example` for what each variable does. It is never
committed to the repository and `deploy.sh` never overwrites it.

Then ship the code and bring the app up for the first time:

```bash
PROJECT_ID=your-project ./deploy/gcp/deploy.sh
```

The app is now reachable at the VM's external IP on port 80.

### Subsequent deploys

```bash
PROJECT_ID=your-project ./deploy/gcp/deploy.sh
```

This syncs the current code to the VM and runs `docker compose up -d --build`. The
`postgres_data` volume is untouched, so store data survives.

Out of scope for now: Cloud SQL, HTTPS/TLS termination and CI/CD — the VM serves plain
HTTP on port 80 only.

## Current MVP scope

- Search by store name and address
- Register a store
- Edit store details
- Three-state tracking per payment method
- Master data management through the Django admin site
- A shared password in front of the whole app

Individual accounts, change history, contributor information and an approval flow are planned
for a later stage.
