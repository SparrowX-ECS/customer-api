# Customer API

The SparrowX Labs Customer API is the Customer Experience team's lightweight CRUD service for customer accounts. It uses FastAPI, SQLModel, and PostgreSQL.

The API supports creating, listing/searching, retrieving, updating, and deleting customers. A customer has a required `name` and unique `email`, plus optional `phone` and `company` fields. Names and emails are limited to 100 and 254 characters respectively; phone and company are limited to 30 and 150 characters.

## Run locally

From this directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
uvicorn src.main:app --reload
```

The application reads `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, and `DB_PASSWORD` from the environment.

Run tests with:

```bash
pytest
```

## API and monitoring

- OpenAPI UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- OpenAPI JSON: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- Health: `GET /health`
- Metrics: [http://localhost:8000/metrics](http://localhost:8000/metrics)

Endpoints are `POST /api/customer/`, `GET /api/customer/`, `GET /api/customer/{customer_id}`, `PUT /api/customer/{customer_id}`, and `DELETE /api/customer/{customer_id}`. `GET /api/customer/` accepts `search`, `offset`, and `limit`; search checks name, email, and company.

The importable Grafana example is at `monitoring/grafana-dashboard.json`. It assumes Prometheus scrapes this service and uses the `job="customer-api"` label.

## Docker

```bash
docker build -t customer-api .
docker run --rm --network sparrowx-local -p 8000:8000 \
  --env-file ../.env \
  -e DB_HOST=local-customer-postgres-db \
  -e DB_PORT=5432 \
  -e DB_NAME=customerdb \
  -e DB_USERNAME="$POSTGRES_USER" \
  -e DB_PASSWORD="$POSTGRES_PASSWORD" \
  customer-api
```
