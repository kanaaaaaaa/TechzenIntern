# PayMethodFinder

A web app for searching, registering and updating the payment methods each store accepts.

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
python manage.py migrate
python manage.py createsuperuser  # only if you want the admin site
python manage.py runserver
```

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
  -H 'Content-Type: application/json' -d '{"password":"techzen2026"}' \
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
  `DJANGO_DEBUG` を設定せずに（`true` のまま）起動してください。

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
| `DJANGO_SECRET_KEY` | Required. Any long random string |
| `DJANGO_DEBUG` | `false` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma separated hostnames. Render's own hostname is added automatically |
| `CSRF_TRUSTED_ORIGINS` | Comma separated `https://…` origins, needed to log into the admin site |
| `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` | Optional. Recreates the admin account on every deploy |
| `APP_PASSWORD` | The password visitors type to open the app. Defaults to `techzen2026` |
| `DATABASE_URL` | Optional. Set it to a `postgres://…` URL to move off SQLite |
| `CORS_ALLOWED_ORIGINS` | Only needed if the frontend is hosted separately |

Two things to keep in mind.

- **The database is disposable.** SQLite lives inside the container, so every deploy or
  restart starts from an empty database with the four payment methods seeded again. Set
  `DATABASE_URL` to a PostgreSQL instance when the data needs to survive.
- **The app is behind a shared password.** Visitors enter it once (`techzen2026` by default,
  overridden with `APP_PASSWORD`) and the browser keeps the token it gets back. Everyone who
  knows the password can create, edit and delete stores; there are no individual accounts yet.

## Current MVP scope

- Search by store name and address
- Register a store
- Edit store details
- Three-state tracking per payment method
- Master data management through the Django admin site
- A shared password in front of the whole app

Individual accounts, change history, contributor information and an approval flow are planned
for a later stage.
