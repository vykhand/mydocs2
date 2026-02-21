# Infrastructure & Deployment Guide

**Last updated**: 2026-02-21
**Spec reference**: [docs/specs/infrastructure.md](docs/specs/infrastructure.md)

---

## Table of Contents

1. [Current State Overview](#1-current-state-overview)
2. [Deviations from Spec](#2-deviations-from-spec)
3. [Deployment: Docker Compose (Local)](#3-deployment-docker-compose-local)
4. [Deployment: Self-Hosted Kubernetes](#4-deployment-self-hosted-kubernetes)
5. [Deployment: Azure AKS (CI/CD)](#5-deployment-azure-aks-cicd)

---

## 1. Current State Overview

### 1.1 Architecture

MyDocs is a two-container application: a FastAPI backend and a Vue 3 SPA served by Nginx. All external state lives in MongoDB (managed externally) and persistent volumes.

```
                    ┌──────────────────────────────────────────┐
                    │              Ingress / Port 80            │
                    └────────────────────┬─────────────────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │     UI (Nginx)       │
                              │  - Static SPA files  │
                              │  - /api/* → backend  │
                              └──────────┬──────────┘
                                         │ proxy_pass
                                         ▼
                              ┌─────────────────────┐
                              │  Backend (uvicorn)   │
                              │  - FastAPI :8000     │
                              │  - /app/data volume  │
                              └──────────┬──────────┘
                                         │
                          ┌──────────────┼──────────────┐
                          ▼              ▼              ▼
                    ┌──────────┐  ┌───────────┐  ┌───────────┐
                    │ MongoDB  │  │ Azure DI  │  │ Azure OAI │
                    │(external)│  │ (external)│  │ (external) │
                    └──────────┘  └───────────┘  └───────────┘
```

### 1.2 Container Images

| Image | Base | Port | Entrypoint |
|-------|------|------|------------|
| `mydocs-backend` | `python:3.13-slim` (multi-stage) | 8000 | `uvicorn mydocs.backend.app:create_app --factory` |
| `mydocs-ui` | `nginx:1.27-alpine` (built with `node:22-alpine`) | 80 | Nginx serving SPA + reverse proxy |

### 1.3 File Layout

```
├── .github/workflows/
│   └── deploy-aks.yml              # CI/CD: build → ACR → AKS
├── Dockerfile.backend              # Backend image (multi-stage Python)
├── Dockerfile.ui                   # UI image (multi-stage Node → Nginx)
├── docker-compose.yml              # Local / single-server deployment
├── .env.example                    # Environment variable template
├── deploy/
│   ├── nginx.conf                  # Nginx config for UI container
│   └── k8s/
│       ├── base/                   # Cloud-agnostic K8s manifests
│       │   ├── kustomization.yaml
│       │   ├── namespace.yml
│       │   ├── configmap.yml
│       │   ├── pvc.yml
│       │   ├── backend-deployment.yml
│       │   ├── backend-service.yml
│       │   ├── ui-deployment.yml
│       │   ├── ui-service.yml
│       │   ├── ingress.yml
│       │   └── secret.yml.example  # Template (not applied by Kustomize)
│       └── overlays/
│           ├── self-hosted/
│           │   ├── kustomization.yaml
│           │   ├── README.md
│           │   └── secret.yml      # User-created (gitignored)
│           └── azure/
│               ├── kustomization.yaml
│               └── ingress-patch.yml
```

### 1.4 Deployment Targets

| Target | How to Deploy | Images From | Secrets From |
|--------|--------------|-------------|--------------|
| **Docker Compose** | `docker compose up -d` | Built locally | `.env` file |
| **Self-hosted K8s** | `kubectl apply -k deploy/k8s/overlays/self-hosted/` | Any registry | `secret.yml` (user-created) |
| **Azure AKS** | Push to `azure-deployment` branch | Azure Container Registry | GitHub Secrets → kubectl |

### 1.5 Kustomize Structure

The Kubernetes manifests use a **base + overlays** pattern:

- **Base** (`deploy/k8s/base/`): Contains all resources common across targets. Uses generic image names (`mydocs-backend:latest`, `mydocs-ui:latest`). Does **not** include the Secret — each overlay manages secrets independently.
- **Self-hosted overlay**: References base + a user-created `secret.yml`.
- **Azure overlay**: References base + an ingress patch adding TLS via cert-manager. Images and secrets are injected dynamically by CI/CD.

### 1.6 Authentication

Microsoft Entra ID (Azure AD) with OAuth 2.0 / OpenID Connect. The Vue SPA obtains tokens via `@azure/msal-browser`; the backend validates JWT signatures against Entra's public JWKS. Auth is **disabled** when `ENTRA_TENANT_ID` is unset, enabling zero-config local development.

---

## 2. Deviations from Spec

Comparing the actual files against `docs/specs/infrastructure.md`:

### 2.1 Nginx Config — Additional Features

The spec (Section 2.3) shows a minimal nginx config. The actual `deploy/nginx.conf` adds:

| Addition | Description |
|----------|-------------|
| `types { application/javascript mjs; }` | Custom MIME type for `.mjs` files (Vite output) |
| `location /assets/ { expires 1y; add_header Cache-Control "public, immutable"; }` | Long-lived cache for hashed static assets |

These are **improvements** beyond the spec, not conflicts. The core routing (`/`, `/api/`, `/health`) matches exactly.

### 2.2 Docker Compose Healthcheck Command

| | Spec | Actual |
|-|------|--------|
| **Healthcheck** | `curl -f http://localhost:8000/health` | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"` |

The actual implementation avoids a `curl` dependency in the `python:3.13-slim` image (which doesn't include curl). This is a practical improvement.

### 2.3 Environment Variables — Additional Entries in `.env.example`

The `.env.example` file includes variables beyond what the spec's Section 4.2 table lists:

| Variable | Purpose | In Spec? |
|----------|---------|----------|
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version | No |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Blob Storage (connection string auth) | No (planned P1/P2 per spec §10) |
| `AZURE_STORAGE_ACCOUNT_NAME` | Azure Blob Storage (account name) | No |
| `AZURE_STORAGE_ACCOUNT_KEY` | Azure Blob Storage (account key auth) | No |
| `AZURE_STORAGE_CONTAINER_NAME` | Azure Blob Storage container | No |
| `MYDOCS_STORAGE_BACKEND` | `local` or `azure_blob` | No |
| `MYDOCS_DATA_FOLDER` | Overrides data directory | No (spec uses `DATA_FOLDER`) |
| `MYDOCS_CONFIG_ROOT` | Overrides config directory | No (spec uses `CONFIG_ROOT`) |
| `SERVICE_NAME` | Service name for logging | No |
| `LOG_LEVEL` | Log verbosity | No |

The Azure Blob Storage variables reflect features already implemented ahead of the spec's P1/P2 roadmap.

### 2.4 Environment Variable Name Prefix

The docker-compose.yml uses `DATA_FOLDER` and `CONFIG_ROOT` (matching the spec), while `.env.example` uses `MYDOCS_DATA_FOLDER` and `MYDOCS_CONFIG_ROOT`. The backend likely supports both; the compose file explicitly sets the non-prefixed names.

### 2.5 Secret Template — Consistent with Spec

The `secret.yml.example` includes exactly the 10 keys documented in the spec (Section 5.2). No deviation.

### 2.6 CI/CD Pipeline — Consistent with Spec

The `deploy-aks.yml` workflow matches the spec (Section 8.2) in structure and behavior:
- Triggers: push/PR to `azure-deployment` + manual dispatch
- Build job: OIDC login, ACR login, build & push with SHA + latest tags
- Deploy job: namespace creation, secrets from GitHub Secrets, `kustomize edit set image`, `kubectl apply -k`, rollout wait

The only minor naming difference: the spec's variables table says `AKS_CLUSTER_NAME`, and the workflow uses `vars.AKS_CLUSTER_NAME` as input but maps it to env `AKS_CLUSTER`. This is consistent — the GitHub variable is indeed named `AKS_CLUSTER_NAME`.

### 2.7 Summary

| Area | Status |
|------|--------|
| Dockerfiles | Matches spec exactly |
| docker-compose.yml | Matches spec (healthcheck improved) |
| Nginx config | Matches spec + production improvements |
| K8s base manifests | Matches spec exactly |
| K8s overlays | Matches spec exactly |
| CI/CD workflow | Matches spec exactly |
| Environment variables | Superset of spec (additional storage/config vars) |
| Authentication flow | Matches spec exactly |

**No breaking deviations.** All differences are additive improvements or features implemented ahead of the roadmap.

---

## 3. Deployment: Docker Compose (Local)

### 3.1 Prerequisites

- Docker Engine 20+ and Docker Compose v2
- A MongoDB instance (local, Docker, or Atlas)
- (Optional) Azure API keys for Document Intelligence and OpenAI features
- (Optional) Microsoft Entra ID app registration for OAuth

### 3.2 Step-by-Step

**1. Clone the repository:**

```bash
git clone <repo-url>
cd mydocs2
```

**2. Create the environment file:**

```bash
cp .env.example .env
```

Edit `.env` with your values:

```dotenv
# Required — MongoDB
MONGO_URL=mongodb+srv://your-cluster.mongodb.net
MONGO_USER=your_user
MONGO_PASSWORD=your_password
MONGO_DB_NAME=mydocs

# Required — Azure Document Intelligence
AZURE_DI_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_DI_API_KEY=your-api-key

# Required — Azure OpenAI
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_API_BASE=https://your-resource.openai.azure.com

# Optional — OAuth (leave empty to disable auth in local dev)
ENTRA_TENANT_ID=
ENTRA_CLIENT_ID=
```

**3. Prepare data and config directories:**

```bash
mkdir -p data config
```

Place your `parser.yml` in `config/` if you have custom parsing configuration.

**4. Build and start:**

```bash
docker compose up -d --build
```

**5. Verify:**

```bash
# Check services are running
docker compose ps

# Check backend health
curl http://localhost:8000/health

# Open UI
open http://localhost:80
```

**6. View logs:**

```bash
docker compose logs -f backend
docker compose logs -f ui
```

**7. Stop:**

```bash
docker compose down
```

### 3.3 Enabling OAuth Locally

If you want to test authentication locally:

1. Register an app in Microsoft Entra ID (Azure AD).
2. Set the redirect URI to `http://localhost/`.
3. Fill in `.env`:
   ```dotenv
   ENTRA_TENANT_ID=your-tenant-id
   ENTRA_CLIENT_ID=your-client-id
   ```
4. Rebuild the UI with build args:
   ```bash
   docker compose build --build-arg VITE_ENTRA_CLIENT_ID=your-client-id \
     --build-arg VITE_ENTRA_AUTHORITY=https://login.microsoftonline.com/your-tenant-id \
     ui
   docker compose up -d
   ```

### 3.4 Using Azure Blob Storage

To use Azure Blob Storage instead of local file storage:

```dotenv
MYDOCS_STORAGE_BACKEND=azure_blob
# Option A: Connection string
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
# Option B: Account name + key
AZURE_STORAGE_ACCOUNT_NAME=youraccount
AZURE_STORAGE_ACCOUNT_KEY=your-key
# Option C: Account name only (uses DefaultAzureCredential)
AZURE_STORAGE_ACCOUNT_NAME=youraccount

AZURE_STORAGE_CONTAINER_NAME=managed
```

---

## 4. Deployment: Self-Hosted Kubernetes

### 4.1 Prerequisites

- A Kubernetes cluster (any: on-prem, Minikube, k3s, kind, etc.)
- `kubectl` configured to connect to your cluster
- `kustomize` CLI (or `kubectl` v1.21+ which includes it)
- An Nginx Ingress Controller installed in the cluster
- A container registry accessible from your cluster
- Docker for building images

### 4.2 Step-by-Step

**1. Build and push images:**

```bash
TAG=$(git rev-parse --short HEAD)

# Build backend
docker build -f Dockerfile.backend -t your-registry/mydocs-backend:$TAG .

# Build UI (with optional OAuth build args)
docker build -f Dockerfile.ui \
  --build-arg VITE_ENTRA_CLIENT_ID=your-client-id \
  --build-arg VITE_ENTRA_AUTHORITY=https://login.microsoftonline.com/your-tenant-id \
  -t your-registry/mydocs-ui:$TAG .

# Push both
docker push your-registry/mydocs-backend:$TAG
docker push your-registry/mydocs-ui:$TAG
```

If using a local cluster (Minikube, kind) without a registry, load images directly:

```bash
# Minikube
minikube image load your-registry/mydocs-backend:$TAG
minikube image load your-registry/mydocs-ui:$TAG

# kind
kind load docker-image your-registry/mydocs-backend:$TAG
kind load docker-image your-registry/mydocs-ui:$TAG
```

**2. Create the secrets file:**

```bash
cp deploy/k8s/base/secret.yml.example deploy/k8s/overlays/self-hosted/secret.yml
```

Edit `deploy/k8s/overlays/self-hosted/secret.yml` and fill in all values:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mydocs-secrets
  namespace: mydocs
type: Opaque
stringData:
  MONGO_URL: "mongodb+srv://your-cluster.mongodb.net"
  MONGO_USER: "your_user"
  MONGO_PASSWORD: "your_password"
  MONGO_DB_NAME: "mydocs"
  AZURE_DI_ENDPOINT: "https://your-resource.cognitiveservices.azure.com"
  AZURE_DI_API_KEY: "your-key"
  AZURE_OPENAI_API_KEY: "your-key"
  AZURE_OPENAI_API_BASE: "https://your-resource.openai.azure.com"
  ENTRA_TENANT_ID: ""
  ENTRA_CLIENT_ID: ""
```

**3. Set image references:**

```bash
cd deploy/k8s/overlays/self-hosted
kustomize edit set image \
  mydocs-backend=your-registry/mydocs-backend:$TAG \
  mydocs-ui=your-registry/mydocs-ui:$TAG
```

**4. (Optional) Customize the ingress hostname:**

Edit `deploy/k8s/base/ingress.yml` and replace `mydocs.example.com` with your domain. Or add an ingress patch in the self-hosted overlay.

**5. Deploy:**

```bash
kubectl apply -k deploy/k8s/overlays/self-hosted/
```

**6. Verify:**

```bash
kubectl get pods -n mydocs
kubectl rollout status deployment/backend -n mydocs
kubectl rollout status deployment/ui -n mydocs

# Check logs
kubectl logs -n mydocs deployment/backend
kubectl logs -n mydocs deployment/ui
```

**7. Access the application:**

```bash
# If using an ingress with a proper domain, visit https://your-domain/
# For local clusters without ingress, use port-forwarding:
kubectl port-forward -n mydocs svc/ui 8080:80
# Then open http://localhost:8080
```

### 4.3 Customization Options

| Setting | How to Customize |
|---------|-----------------|
| **Hostname** | Edit `deploy/k8s/base/ingress.yml` or add an ingress patch in the overlay |
| **TLS** | Add a TLS section to the ingress (see `overlays/azure/ingress-patch.yml` as a template) |
| **Storage class** | Add a Kustomize patch overriding `storageClassName` on the PVC |
| **Replicas** | Add a Kustomize patch increasing `replicas` on backend/UI deployments |
| **Ingress class** | Change `ingressClassName` in `ingress.yml` if not using nginx |

### 4.4 Updating

```bash
TAG=$(git rev-parse --short HEAD)

# Build & push new images
docker build -f Dockerfile.backend -t your-registry/mydocs-backend:$TAG .
docker build -f Dockerfile.ui -t your-registry/mydocs-ui:$TAG .
docker push your-registry/mydocs-backend:$TAG
docker push your-registry/mydocs-ui:$TAG

# Update image tags and apply
cd deploy/k8s/overlays/self-hosted
kustomize edit set image \
  mydocs-backend=your-registry/mydocs-backend:$TAG \
  mydocs-ui=your-registry/mydocs-ui:$TAG
kubectl apply -k .
```

---

## 5. Deployment: Azure AKS (CI/CD)

### 5.1 Prerequisites

**Azure Resources** (must be created beforehand):

- An Azure Kubernetes Service (AKS) cluster
- An Azure Container Registry (ACR), attached to the AKS cluster
- A service principal or managed identity with:
  - `AcrPush` role on the ACR
  - `Azure Kubernetes Service Cluster User Role` on the AKS cluster
- Federated credential configured for GitHub OIDC (for passwordless auth)
- (Optional) A DNS record pointing to the AKS ingress controller's external IP
- (Optional) cert-manager installed in the cluster with a `letsencrypt-prod` ClusterIssuer

**MongoDB and API Keys**:

- MongoDB Atlas connection string (or other MongoDB instance reachable from AKS)
- Azure Document Intelligence endpoint and API key
- Azure OpenAI endpoint and API key

**Microsoft Entra ID**:

- An app registration in Entra ID with redirect URI set to your application's URL
- The client ID and tenant ID

### 5.2 GitHub Configuration

#### Secrets (Settings → Secrets and variables → Actions → Secrets)

| Secret | Description | Example |
|--------|-------------|---------|
| `AZURE_CLIENT_ID` | Service principal client ID for OIDC login | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_TENANT_ID` | Azure AD tenant ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `ENTRA_CLIENT_ID` | Entra ID app registration client ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `ENTRA_AUTHORITY` | Entra ID authority URL | `https://login.microsoftonline.com/<tenant-id>` |
| `MONGO_URL` | MongoDB connection string | `mongodb+srv://cluster.mongodb.net` |
| `MONGO_USER` | MongoDB username | `mydocs_user` |
| `MONGO_PASSWORD` | MongoDB password | `***` |
| `MONGO_DB_NAME` | MongoDB database name | `mydocs` |
| `AZURE_DI_ENDPOINT` | Document Intelligence endpoint | `https://mydi.cognitiveservices.azure.com` |
| `AZURE_DI_API_KEY` | Document Intelligence API key | `***` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | `***` |
| `AZURE_OPENAI_API_BASE` | Azure OpenAI endpoint | `https://myoai.openai.azure.com` |

#### Variables (Settings → Secrets and variables → Actions → Variables)

| Variable | Description | Example |
|----------|-------------|---------|
| `ACR_NAME` | Azure Container Registry name (without `.azurecr.io`) | `mydocsacr` |
| `AKS_CLUSTER_NAME` | AKS cluster name | `mydocs-aks` |
| `AKS_RESOURCE_GROUP` | Resource group containing the AKS cluster | `mydocs-rg` |

### 5.3 Trigger a Deployment

**Option A: Push to the deployment branch**

```bash
git checkout azure-deployment
git merge main    # or cherry-pick specific commits
git push origin azure-deployment
```

The workflow will:
1. Build both Docker images and push to ACR (tagged with commit SHA + `latest`)
2. Create/update the K8s secret from GitHub Secrets
3. Stamp the ACR image references into the azure overlay via `kustomize edit set image`
4. Apply the overlay with `kubectl apply -k`
5. Wait for rollout to complete (300s timeout)

**Option B: Manual dispatch**

Go to Actions → "Deploy to Azure AKS" → Run workflow. Optionally provide a custom image tag.

**Option C: Pull request (build only)**

Opening a PR targeting `azure-deployment` will run the build job only (no deploy), validating that images build successfully.

### 5.4 Pipeline Flow

```
push to azure-deployment
        │
        ▼
┌───────────────────────────────┐
│  Build Job                    │
│  1. Checkout                  │
│  2. Azure Login (OIDC)        │
│  3. ACR Login                 │
│  4. Build & push backend      │
│     image (SHA + latest)      │
│  5. Build & push UI image     │
│     (SHA + latest, with       │
│      VITE_ENTRA_* build args) │
└───────────┬───────────────────┘
            │ (push only, not on PR)
            ▼
┌───────────────────────────────┐
│  Deploy Job                   │
│  1. Azure Login (OIDC)        │
│  2. Get AKS credentials       │
│  3. Create namespace          │
│  4. Create K8s secret from    │
│     GitHub Secrets             │
│  5. kustomize edit set image  │
│     (stamp ACR + SHA tag)     │
│  6. kubectl apply -k overlay  │
│  7. Wait for rollout          │
│  8. Post summary              │
└───────────────────────────────┘
```

### 5.5 Post-Deployment Verification

```bash
# Get AKS credentials locally
az aks get-credentials --resource-group mydocs-rg --name mydocs-aks

# Check pods
kubectl get pods -n mydocs

# Check ingress
kubectl get ingress -n mydocs

# Check logs
kubectl logs -n mydocs deployment/backend
kubectl logs -n mydocs deployment/ui

# Check backend health
kubectl port-forward -n mydocs svc/backend 8000:8000
curl http://localhost:8000/health
```

### 5.6 TLS / HTTPS

The Azure overlay patches the base ingress to add TLS via cert-manager:

- Annotation: `cert-manager.io/cluster-issuer: letsencrypt-prod`
- TLS secret: `mydocs-tls`
- Host: `mydocs.example.com` (update in `deploy/k8s/base/ingress.yml`)

**Prerequisites for TLS**:
1. cert-manager installed in the cluster: `kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml`
2. A `ClusterIssuer` named `letsencrypt-prod` configured
3. A DNS A record pointing your domain to the ingress controller's external IP

### 5.7 Rollback

```bash
# View deployment history
kubectl rollout history deployment/backend -n mydocs

# Roll back to previous version
kubectl rollout undo deployment/backend -n mydocs
kubectl rollout undo deployment/ui -n mydocs
```

---

## Appendix: Environment Variable Reference

| Variable | Required | Default | Used By | Description |
|----------|----------|---------|---------|-------------|
| `MONGO_URL` | Yes | — | Backend | MongoDB connection string |
| `MONGO_USER` | Yes | — | Backend | MongoDB username |
| `MONGO_PASSWORD` | Yes | — | Backend | MongoDB password |
| `MONGO_DB_NAME` | Yes | — | Backend | MongoDB database name |
| `AZURE_DI_ENDPOINT` | Yes | — | Backend | Azure Document Intelligence endpoint |
| `AZURE_DI_API_KEY` | Yes | — | Backend | Azure Document Intelligence API key |
| `AZURE_OPENAI_API_KEY` | Yes | — | Backend | Azure OpenAI API key |
| `AZURE_OPENAI_API_BASE` | Yes | — | Backend | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_VERSION` | No | `2024-12-01-preview` | Backend | Azure OpenAI API version |
| `ENTRA_TENANT_ID` | No | (empty = auth disabled) | Backend | Azure AD tenant ID |
| `ENTRA_CLIENT_ID` | No | — | Backend | Entra ID app registration client ID |
| `ENTRA_ISSUER` | No | Auto-derived from tenant | Backend | Token issuer URL override |
| `VITE_ENTRA_CLIENT_ID` | No | — | UI (build arg) | Entra client ID baked into SPA |
| `VITE_ENTRA_AUTHORITY` | No | — | UI (build arg) | Entra authority URL baked into SPA |
| `MYDOCS_STORAGE_BACKEND` | No | `local` | Backend | `local` or `azure_blob` |
| `AZURE_STORAGE_CONNECTION_STRING` | No | — | Backend | Azure Blob connection string |
| `AZURE_STORAGE_ACCOUNT_NAME` | No | — | Backend | Azure Blob account name |
| `AZURE_STORAGE_ACCOUNT_KEY` | No | — | Backend | Azure Blob account key |
| `AZURE_STORAGE_CONTAINER_NAME` | No | — | Backend | Azure Blob container name |
| `DATA_FOLDER` | No | `/app/data` | Backend | Data directory (container path) |
| `CONFIG_ROOT` | No | `/app/config` | Backend | Config directory (container path) |
| `SERVICE_NAME` | No | `mydocs` | Backend | Service name for logging |
| `LOG_LEVEL` | No | `INFO` | Backend | Log verbosity |
