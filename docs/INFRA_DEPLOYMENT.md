# Infrastructure & Deployment Guide

**Last updated**: 2026-02-23
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

### 2.5 Secret Template — Superset of Spec

The `secret.yml.example` includes the 10 keys documented in the spec (Section 5.2) plus 3 additional storage backend variables (`MYDOCS_STORAGE_BACKEND`, `AZURE_STORAGE_ACCOUNT_NAME`, `AZURE_STORAGE_CONTAINER_NAME`) for Azure Blob Storage support. Two more options (`AZURE_STORAGE_ACCOUNT_KEY`, `AZURE_STORAGE_CONNECTION_STRING`) are present as comments. This reflects the storage features implemented ahead of the spec's P1/P2 roadmap.

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

**Local tools**:

- Azure CLI (`brew install azure-cli` on macOS)
- `kubectl` (included with Azure CLI or standalone)
- `helm` (`brew install helm` on macOS)
- `gh` CLI for GitHub operations

**External services** (existing):

- MongoDB Atlas (or other MongoDB instance) — connection string, user, password
- Azure Document Intelligence — endpoint and API key
- Azure OpenAI — endpoint and API key

### 5.2 Create Azure Resources

Resource naming convention: `{type}-{project}` (e.g., `rg-mydocs`, `aks-mydocs`). ACR names must be alphanumeric only (e.g., `acrmydocs`).

```bash
# Set variables
RG=rg-mydocs
LOCATION=westeurope    # or your preferred region
AKS_NAME=aks-mydocs
ACR_NAME=acrmydocs     # must be globally unique, alphanumeric only
```

**1. Register resource providers** (first-time only per subscription):

```bash
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.ContainerService
# Wait for registration (can take 1-2 minutes)
az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv
az provider show -n Microsoft.ContainerService --query registrationState -o tsv
```

**2. Create resource group and ACR:**

```bash
az group create --name $RG --location $LOCATION
az acr create --name $ACR_NAME --resource-group $RG --sku Basic --location $LOCATION
```

**3. Create AKS cluster:**

```bash
# Note: Standard_B2s may not be available in all subscriptions.
# Use standard_b2s_v2 (2 vCPU, 8GB RAM) as a budget alternative.
az aks create \
  --name $AKS_NAME \
  --resource-group $RG \
  --location $LOCATION \
  --node-count 1 \
  --node-vm-size standard_b2s_v2 \
  --enable-managed-identity \
  --generate-ssh-keys

# Attach ACR to AKS (grants pull access)
az aks update --name $AKS_NAME --resource-group $RG --attach-acr $ACR_NAME
```

**4. Get kubectl credentials and install NGINX ingress:**

```bash
az aks get-credentials --resource-group $RG --name $AKS_NAME

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace --namespace ingress-nginx \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz
```

**5. Get the ingress external IP** (wait 1-2 minutes after install):

```bash
kubectl get service --namespace ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

Save this IP — you'll need it for the ingress hostname and OAuth redirect URI.

**6. Update the ingress hostname:**

Edit `deploy/k8s/base/ingress.yml` and replace the host with your domain or `{IP}.nip.io` for quick testing:

```yaml
rules:
  - host: <INGRESS_IP>.nip.io   # e.g., 20.103.70.81.nip.io
```

### 5.3 Set Up GitHub OIDC (CI/CD Authentication)

The CI/CD pipeline uses OIDC federated credentials — no stored passwords.

```bash
# Create app registration for GitHub Actions
APP_ID=$(az ad app create --display-name sp-mydocs-github --query appId -o tsv)
SP_ID=$(az ad sp create --id $APP_ID --query id -o tsv)

# Assign roles
ACR_ID=$(az acr show --name $ACR_NAME --query id -o tsv)
AKS_ID=$(az aks show --name $AKS_NAME --resource-group $RG --query id -o tsv)
az role assignment create --assignee $SP_ID --role AcrPush --scope $ACR_ID
az role assignment create --assignee $SP_ID --role "Azure Kubernetes Service Cluster User Role" --scope $AKS_ID

# Create federated credential for the azure-deployment branch
# Replace OWNER/REPO with your GitHub repo
az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "github-azure-deployment",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:OWNER/REPO:ref:refs/heads/azure-deployment",
  "audiences": ["api://AzureADTokenExchange"]
}'

# Note these values for GitHub secrets:
TENANT_ID=$(az account show --query tenantId -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "AZURE_CLIENT_ID: $APP_ID"
echo "AZURE_TENANT_ID: $TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID: $SUBSCRIPTION_ID"
```

### 5.4 Set Up Microsoft Entra ID (OAuth)

**1. Create the app registration:**

```bash
ENTRA_APP_ID=$(az ad app create \
  --display-name "MyDocs App" \
  --sign-in-audience AzureADMyOrg \
  --query appId -o tsv)
ENTRA_OBJECT_ID=$(az ad app show --id $ENTRA_APP_ID --query id -o tsv)
```

**2. Configure the Application ID URI and API scope:**

The MSAL SPA requests `api://{clientId}/access_as_user` — this scope must exist:

```bash
# Set Application ID URI
az ad app update --id $ENTRA_APP_ID \
  --identifier-uris "api://$ENTRA_APP_ID"

# Add the access_as_user scope
SCOPE_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
az ad app update --id $ENTRA_APP_ID \
  --set "api={\"oauth2PermissionScopes\":[{
    \"adminConsentDescription\":\"Access MyDocs as a user\",
    \"adminConsentDisplayName\":\"Access as user\",
    \"id\":\"$SCOPE_ID\",
    \"isEnabled\":true,
    \"type\":\"User\",
    \"userConsentDescription\":\"Access MyDocs on your behalf\",
    \"userConsentDisplayName\":\"Access as user\",
    \"value\":\"access_as_user\"
  }]}"
```

**3. Set access token version to v2:**

By default, Entra issues v1 tokens (issuer: `sts.windows.net`). The backend accepts both v1 and v2 issuers, but v2 is preferred:

```bash
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$ENTRA_OBJECT_ID" \
  --headers "Content-Type=application/json" \
  --body '{"api":{"requestedAccessTokenVersion":2}}'
```

**4. Add SPA redirect URI:**

MSAL requires HTTPS for SPA redirect URIs (except localhost). For quick testing without a domain, use a self-signed certificate with nip.io:

```bash
# Add SPA platform redirect URI
az ad app update --id $ENTRA_APP_ID \
  --set spa="{\"redirectUris\":[\"https://<INGRESS_IP>.nip.io/\"]}"
```

**5. Create the service principal and restrict access:**

```bash
SP_OBJ_ID=$(az ad sp create --id $ENTRA_APP_ID --query id -o tsv)

# Enable "User assignment required" (only assigned users can log in)
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$SP_OBJ_ID" \
  --headers "Content-Type=application/json" \
  --body '{"appRoleAssignmentRequired": true}'
```

**6. Invite and assign users:**

For external users (personal Microsoft accounts like `user@outlook.com`):

```bash
# Invite as guest
USER_ID=$(az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/invitations" \
  --headers "Content-Type=application/json" \
  --body '{
    "invitedUserEmailAddress": "user@outlook.com",
    "inviteRedirectUrl": "https://<INGRESS_IP>.nip.io/",
    "sendInvitationMessage": true
  }' --query invitedUser.id -o tsv)

# Assign user to the app (default role)
az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$SP_OBJ_ID/appRoleAssignments" \
  --headers "Content-Type=application/json" \
  --body "{
    \"principalId\": \"$USER_ID\",
    \"resourceId\": \"$SP_OBJ_ID\",
    \"appRoleId\": \"00000000-0000-0000-0000-000000000000\"
  }"
```

The invited user must accept the email invitation before they can sign in.

For tenant-internal users, skip the invitation step and use their Object ID directly.

### 5.5 TLS / HTTPS

MSAL SPA requires HTTPS. Choose one approach:

**Option A: Self-signed certificate** (quick testing):

```bash
INGRESS_IP=<your-ingress-ip>

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /tmp/mydocs-tls.key -out /tmp/mydocs-tls.crt \
  -subj "/CN=$INGRESS_IP.nip.io" \
  -addext "subjectAltName=DNS:$INGRESS_IP.nip.io"

kubectl create secret tls mydocs-tls \
  --cert=/tmp/mydocs-tls.crt --key=/tmp/mydocs-tls.key \
  --namespace=mydocs --dry-run=client -o yaml | kubectl apply -f -

# Update the ingress to use TLS (apply inline or edit ingress.yml)
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mydocs-ingress
  namespace: mydocs
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts: ["$INGRESS_IP.nip.io"]
      secretName: mydocs-tls
  rules:
    - host: $INGRESS_IP.nip.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: ui, port: { number: 80 } }
EOF
```

Users will see a browser certificate warning (click through to proceed).

**Option B: cert-manager with Let's Encrypt** (production — requires a real domain):

The Azure overlay (`deploy/k8s/overlays/azure/ingress-patch.yml`) adds TLS via cert-manager:

1. Install cert-manager: `kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml`
2. Create a `ClusterIssuer` named `letsencrypt-prod`
3. Point a DNS A record to the ingress controller's external IP
4. Re-enable the TLS patch in `deploy/k8s/overlays/azure/kustomization.yaml`

### 5.6 GitHub Configuration

#### Secrets (Settings → Secrets and variables → Actions → Secrets)

| Secret | Description | Example |
|--------|-------------|---------|
| `AZURE_CLIENT_ID` | Service principal client ID (from §5.3) | `xxxxxxxx-xxxx-...` |
| `AZURE_TENANT_ID` | Azure AD tenant ID | `xxxxxxxx-xxxx-...` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | `xxxxxxxx-xxxx-...` |
| `ENTRA_CLIENT_ID` | OAuth app client ID (from §5.4) | `xxxxxxxx-xxxx-...` |
| `ENTRA_TENANT_ID` | Same as `AZURE_TENANT_ID` | `xxxxxxxx-xxxx-...` |
| `ENTRA_AUTHORITY` | Entra authority URL | `https://login.microsoftonline.com/<tenant-id>` |
| `MONGO_URL` | MongoDB connection string | `mongodb+srv://cluster.mongodb.net` |
| `MONGO_USER` | MongoDB username | `mydocs_user` |
| `MONGO_PASSWORD` | MongoDB password | `***` |
| `MONGO_DB_NAME` | MongoDB database name | `mydocs` |
| `AZURE_DI_ENDPOINT` | Document Intelligence endpoint | `https://mydi.cognitiveservices.azure.com` |
| `AZURE_DI_API_KEY` | Document Intelligence API key | `***` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | `***` |
| `AZURE_OPENAI_API_BASE` | Azure OpenAI endpoint | `https://myoai.openai.azure.com` |
| `MYDOCS_STORAGE_BACKEND` | `azure_blob` or `local` | `azure_blob` |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name | `mydocsstoracc001` |
| `AZURE_STORAGE_ACCOUNT_KEY` | Storage account key (if not using managed identity) | `***` |
| `AZURE_STORAGE_CONTAINER_NAME` | Blob container name | `docs` |

You can set these via `gh` CLI:

```bash
gh secret set SECRET_NAME --body "value" --repo OWNER/REPO
```

#### Variables (Settings → Secrets and variables → Actions → Variables)

| Variable | Description | Example |
|----------|-------------|---------|
| `ACR_NAME` | ACR name (without `.azurecr.io`) | `acrmydocs` |
| `AKS_CLUSTER_NAME` | AKS cluster name | `aks-mydocs` |
| `AKS_RESOURCE_GROUP` | Resource group | `rg-mydocs` |

```bash
gh variable set VAR_NAME --body "value" --repo OWNER/REPO
```

### 5.7 Trigger a Deployment

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

### 5.8 Pipeline Flow

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

### 5.9 Post-Deployment Verification

```bash
# Get AKS credentials locally
az aks get-credentials --resource-group rg-mydocs --name aks-mydocs

# Check pods
kubectl get pods -n mydocs

# Check ingress
kubectl get ingress -n mydocs

# Check logs
kubectl logs -n mydocs deployment/backend
kubectl logs -n mydocs deployment/ui

# Check backend health via port-forward
kubectl port-forward -n mydocs svc/backend 8000:8000
curl http://localhost:8000/health
```

### 5.10 Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Backend `CrashLoopBackOff` with MongoDB SSL error | AKS outbound IP not in MongoDB Atlas allowlist | Get IP: `az aks show --name aks-mydocs --resource-group rg-mydocs --query "networkProfile.loadBalancerProfile.effectiveOutboundIPs[].id" -o tsv \| xargs -I{} az network public-ip show --ids {} --query ipAddress -o tsv`. Add it to Atlas Network Access. |
| Login succeeds but immediate sign-out (401 loop) | JWT audience mismatch — token has `aud=api://{clientId}` but backend expects `{clientId}` | Backend already accepts both formats. Ensure the Application ID URI (`api://{clientId}`) and `access_as_user` scope are configured on the app registration. |
| Login succeeds but immediate sign-out (issuer mismatch) | Entra issues v1 tokens with `iss=https://sts.windows.net/{tenant}/` | Backend accepts both v1 and v2 issuers. Optionally set `accessTokenAcceptedVersion: 2` on the app to get v2 tokens. |
| Blank page on HTTP | MSAL SPA requires HTTPS for redirect URIs (except localhost) | Set up TLS (self-signed or cert-manager). See §5.5. |
| Upload fails with `ClientAuthenticationError` on Blob Storage | Pod can't authenticate with Azure Blob Storage | Add `AZURE_STORAGE_ACCOUNT_KEY` as a GitHub Secret, or configure workload identity with `Storage Blob Data Contributor` role. |
| `Standard_B2s` not available | VM size restricted in subscription | Use `standard_b2s_v2` or check available sizes: `az vm list-skus --location westeurope --size Standard_B --output table` |
| Resource provider not registered | First use of ACR/AKS in subscription | Run `az provider register --namespace Microsoft.ContainerRegistry` (and `Microsoft.ContainerService`). Wait 1-2 minutes. |

### 5.11 Rollback

```bash
# View deployment history
kubectl rollout history deployment/backend -n mydocs

# Roll back to previous version
kubectl rollout undo deployment/backend -n mydocs
kubectl rollout undo deployment/ui -n mydocs
```

---

## 6. Storage Backend Selection

The application supports two storage backends for managed files. The choice of backend interacts with the deployment target:

### 6.1 Which Backend to Use

| Deployment Target | Recommended Backend | Why |
|-------------------|-------------------|-----|
| **Docker Compose** (local dev) | `local` | Simplest. Files on host via bind mount. No cloud credentials. |
| **Docker Compose** (staging) | `azure_blob` | Mirrors production. Use Azurite emulator or real storage account. |
| **Self-hosted K8s** (1 replica) | `local` | PVC is sufficient. Simple to operate. |
| **Self-hosted K8s** (multi-replica) | `azure_blob` | Avoids `ReadWriteMany` PVC requirement. |
| **Azure AKS** | `azure_blob` | Native fit. Uses managed identity. No PVC for files. Scales horizontally. |

### 6.2 Impact on PVC

| Backend | PVC at `/app/data` | Size Guidance |
|---------|-------------------|---------------|
| `local` | **Required** — stores all managed files, uploads, sidecars, DI cache | 10Gi+ depending on document volume |
| `azure_blob` | **Optional** — only for upload staging and DI cache | 2Gi is typically sufficient |

### 6.3 Impact on Ingestion Mode

| Ingestion Mode | `local` backend | `azure_blob` backend |
|---------------|-----------------|---------------------|
| **Managed** (upload/ingest) | Files copied to PVC `/app/data/managed/` | Files uploaded to Blob container |
| **External** (ingest with path) | Original path must be accessible from container | Original path must be accessible from container (impractical in AKS — use managed mode) |

**Recommendation for K8s/AKS**: Always use managed mode. Use the upload endpoint (`POST /api/v1/documents/upload`) or ingest with `storage_mode: managed`. External mode requires manual volume mounts for the original file paths.

### 6.4 Migrating Between Backends

When moving from Docker Compose (local) to AKS (azure_blob), migrate existing files:

```bash
# Via CLI
mydocs sync migrate --from local --to azure_blob --dry-run   # preview
mydocs sync migrate --from local --to azure_blob              # execute

# Via API
POST /api/v1/sync/migrate/plan    {"source_backend": "local", "target_backend": "azure_blob"}
POST /api/v1/sync/migrate/execute {"source_backend": "local", "target_backend": "azure_blob"}
```

After migration, rebuild the database from the target backend:

```bash
mydocs sync run
```

Migration is idempotent — re-running skips files already on the target. Use `--delete-source` to clean up source files after a successful migration.

### 6.5 AKS GitHub Secrets for Azure Blob Storage

When using `azure_blob` backend with AKS CI/CD, add these GitHub Secrets:

| Secret | Value | Notes |
|--------|-------|-------|
| `MYDOCS_STORAGE_BACKEND` | `azure_blob` | Enables Blob backend |
| `AZURE_STORAGE_ACCOUNT_NAME` | Your storage account name | Required |
| `AZURE_STORAGE_ACCOUNT_KEY` | Storage account key | Required unless using workload identity |
| `AZURE_STORAGE_CONTAINER_NAME` | `managed` (or custom) | Container for managed files |

**Authentication options** (choose one):
- **Account key** (simplest): Set `AZURE_STORAGE_ACCOUNT_KEY` as a GitHub Secret. The CI/CD pipeline injects it into the K8s secret.
- **Workload identity** (more secure, no stored keys): Configure AKS workload identity and assign the pod identity the `Storage Blob Data Contributor` role on the storage account. Omit `AZURE_STORAGE_ACCOUNT_KEY` — the SDK uses `DefaultAzureCredential` automatically.

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
