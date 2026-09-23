# Customer API

The SparrowX Labs Customer API is the Customer Experience team's lightweight CRUD service for customer accounts. It is owned by Alex Morgan and uses FastAPI, SQLModel, and SQLite.

The API supports creating, listing/searching, retrieving, updating, and deleting customers. A customer has a required `name` and unique `email`, plus optional `phone` and `company` fields. Names and emails are limited to 100 and 254 characters respectively; phone and company are limited to 30 and 150 characters.

## Run locally

From this directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
uvicorn app:app --reload
```

SQLite is stored in `customer.db` by default. Set `CUSTOMER_API_DATABASE_URL` to use another SQLite URL, for example `sqlite:///./local.db`.

Run tests with:

```bash
pytest
```

## API and monitoring

- OpenAPI UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- OpenAPI JSON: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- Health: `GET /health`
- Metrics: [http://localhost:8000/metrics](http://localhost:8000/metrics)

Endpoints are `POST /customers`, `GET /customers`, `GET /customers/{customer_id}`, `PUT /customers/{customer_id}`, and `DELETE /customers/{customer_id}`. `GET /customers` accepts `search`, `offset`, and `limit`; search checks name, email, and company.

The importable Grafana example is at `monitoring/grafana-dashboard.json`. It assumes Prometheus scrapes this service and uses the `job="customer-api"` label.

## Docker

```bash
docker build -t customer-api .
docker run --rm -p 8000:8000 -v customer-api-data:/data customer-api
```

The container runs as a non-root user and persists its SQLite database in `/data`.
