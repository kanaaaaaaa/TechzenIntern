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

There is no route for `/`, so opening <http://127.0.0.1:8000/> returns 404. That is expected — the backend only serves the API and the admin site.

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

## Current MVP scope

- Search by store name and address
- Register a store
- Edit store details
- Three-state tracking per payment method
- Master data management through the Django admin site

Authentication, change history, contributor information and an approval flow are planned for a later stage.
