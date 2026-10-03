# Customer API

Customer account management service for the fictional SparrowX SaaS platform. This repository is a demonstration workload used to show how a PostgreSQL-backed microservice can be onboarded to AWS ECS/Fargate and deployed consistently to separate `dev` and `prod` environments.

## Service responsibilities

- Customer CRUD and search operations.
- PostgreSQL persistence in the service’s dedicated `customerdb` database.
- Health checks for ECS/ALB and deployment smoke tests.
- Prometheus-compatible metrics for future observability.

## API documentation

When the service is running, FastAPI provides interactive documentation at:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI schema: `/openapi.json`

The main API is available under `/api/customers`:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/customers/` | Create a customer |
| `GET` | `/api/customers/` | List or search customers |
| `GET` | `/api/customers/{customer_id}` | Retrieve a customer |
| `PUT` | `/api/customers/{customer_id}` | Update a customer |
| `DELETE` | `/api/customers/{customer_id}` | Delete a customer |
| `GET` | `/health` | Container/target-group health check |
| `GET` | `/api/customers/health` | API smoke-test health check |
| `GET` | `/metrics` | Prometheus metrics; excluded from OpenAPI |

For a deployed environment, append these paths to that environment’s base URL.

## Runtime environment variables

These variables are supplied to the container by the deployment template. Database credentials are injected from AWS Secrets Manager in ECS.

| Variable | Required | Description |
| --- | --- | --- |
| `DB_HOST` | Yes | Private RDS PostgreSQL endpoint for `customerdb`. |
| `DB_PORT` | No | PostgreSQL port; defaults to `5432`. |
| `DB_NAME` | Yes | Database name, normally `customerdb`. |
| `DB_USERNAME` | Yes | Database username from the service secret. |
| `DB_PASSWORD` | Yes | Database password from the service secret. |
| `CORS_ALLOW_ORIGINS` | No | Comma-separated browser origins; defaults to local development origins. |

## Local development

Install dependencies and run the test suite:

```bash
python -m pip install -r requirements-dev.txt
pytest
```

Run the API locally with PostgreSQL environment variables configured:

```bash
uvicorn src.main:app --reload --port 8000
```

Then open <http://localhost:8000/docs>.

## CI/CD cycle

This repository delegates common delivery logic to pinned reusable workflows in [`workflows-templates`](https://github.com/SparrowX-ECS/workflows-templates).

### Pull request: validate and build

For pull requests targeting `main`, the pipeline:

1. Detects whether application or deployment-relevant files changed.
2. Runs the Python test suite with PostgreSQL.
3. Builds a Docker image tagged with the Git commit SHA.
4. Skips rebuilding if that immutable tag already exists in ECR.
5. Scans the image with Trivy.
6. Publishes image tag, digest, repository, and security metadata to the development SSM parameter.

### Merge to `main`: deploy development

The development workflow resolves the published image metadata, deploys the exact image to the `dev` ECS service, waits for CloudFormation/ECS deployment completion, runs the configured smoke test, and publishes the successful tag and digest as the production candidate.

### Manual production promotion

The production workflow requires the operator to type `PROMOTE`. It resolves the candidate image, verifies the source digest, copies the exact image by digest from the `dev` ECR repository to the `prod` ECR repository, deploys it to the production ECS service, runs the production smoke test, and records the deployed metadata.

This is the project’s **Build Once, Promote Many** model: production is not rebuilt from source.

## Environments and deployment tracking

The repository has two deployment environments:

- `dev`: automatically deployed from `main` after CI succeeds.
- `prod`: promoted manually after the development deployment and smoke test succeed.

Each environment has its own ECS service stack, ECR namespace, configuration file, URL, deployment metadata, and GitHub deployment history. The files [`ecs-parameters-dev.yaml`](ecs-parameters-dev.yaml) and [`ecs-parameters-prod.yaml`](ecs-parameters-prod.yaml) define the service-specific settings for each environment.

## Rollback options

### Git revert

Use this when the desired source or deployment configuration is wrong. Revert the problematic commit and merge the revert. The normal CI/CD pipeline tests, builds, scans, and deploys the corrective commit.

### Quicker manual image rollback

Use this when production needs to return quickly to a previously deployed image without rebuilding.

1. Open the repository’s **Deployments** tab on GitHub.
2. Select the `prod` environment.
3. Open the desired previous successful deployment.
4. Copy the deployed image tag from the deployment details/summary.
5. Open **Actions → Manual Rollback Production To Selected Image Tag**.
6. Select **Run workflow**, enter `ROLLBACK` as the confirmation, and paste the image tag.
7. The workflow redeploys that immutable image to `prod`, runs the production smoke test, and publishes the rollback metadata.

ECS also has a deployment circuit breaker enabled in the shared CloudFormation service template. It can automatically roll an unhealthy rolling deployment back to the previous task definition.

## Repository variables

These are GitHub repository or environment variables used by the workflows. They are not application runtime variables.

| Variable | Description |
| --- | --- |
| `AWS_ACCOUNT_ID` | AWS account containing the environment resources and ECR repositories. |
| `AWS_REGION` | AWS region used by GitHub Actions and the ECS platform. |
| `AWS_ROLE_NAME` | IAM role name assumed through GitHub OIDC. |
| `DEV_BASE_URL` | Development smoke-test origin, including protocol and domain, for example `https://sparrowx-dev.example.com`. |
| `DEV_DEPLOYED_PARAM_STORE_PATH` | SSM Parameter Store path containing the image last successfully deployed to `dev`. |
| `PROD_BASE_URL` | Production smoke-test origin, including protocol and domain, for example `https://sparrowx-prod.example.com`. |
| `PROD_CANDIDATE_PARAM_STORE_PATH` | SSM path containing the image promoted as the production candidate after successful development smoke tests. |
| `PROD_DEPLOYED_PARAM_STORE_PATH` | SSM path containing the image last successfully deployed to `prod`. |

`DEV_BASE_URL` and `PROD_BASE_URL` must be protocol plus domain only, without an API path; the shared smoke-test workflow appends the path from the selected ECS parameters file.

## Container and deployment configuration

- Container port: `8000`.
- Development ALB path: `/api/customers/*`.
- Health check: `/health`.
- Smoke-test path: `/api/customers/health`.
- Database: enabled in both environments.
- Image tags: immutable Git commit SHAs.

## License

This is a proprietary portfolio project. It is publicly viewable but not open source. All rights are reserved. See [LICENSE.md](LICENSE.md).
