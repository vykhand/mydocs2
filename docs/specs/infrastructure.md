# Infrastructure Specification

**Version**: 1.0
**Status**: Draft

**Related Specs**: [backend.md](backend.md) (API, configuration), [UI.md](UI.md) (frontend SPA)

---

## 1. Overview

This specification defines how the MyDocs application is packaged and deployed. Two deployment models are supported:

| Model | Target | Orchestration |
|-------|--------|---------------|
| **Docker Compose** | Local development, single-server deployments | `docker compose up` |
| **Kubernetes** | Production, multi-node clusters | Helm chart or raw manifests |

### 1.1 Scope

**In scope**: backend (FastAPI), UI (Vue 3 SPA), networking between them, file storage volumes.

**Out of scope**: MongoDB -- assumed to be an external managed service (e.g. MongoDB Atlas) or a separately administered instance. The connection is configured via environment variables.

### 1.2 Design Principles

- **Twelve-factor app** -- configuration via environment variables, no baked-in secrets.
- **Minimal images** -- multi-stage builds, slim base images.
- **Single responsibility** -- one process per container.
- **Stateless containers** -- all persistent data lives in external volumes or MongoDB.

---

## 2. Container Images

### 2.1 Backend (`mydocs-backend`)

Multi-stage build based on the Python package in the repository root.

```dockerfile
# Stage 1 -- build
FROM python:3.13-slim AS builder
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY . .
RUN pip install --no-cache-dir .

# Stage 2 -- runtime
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /app /app

EXPOSE 8000
CMD ["uvicorn", "mydocs.backend.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

| Property | Value |
|----------|-------|
| Base image | `python:3.13-slim` |
| Exposed port | `8000` |
| Entrypoint | `uvicorn` with `--factory` flag |
| Health check | `GET /health` |
| Writable paths | `/app/data` (mounted volume), `/tmp` |

### 2.2 UI (`mydocs-ui`)

Multi-stage build: Node for building the SPA, then Nginx to serve static files and reverse-proxy API requests to the backend.

```dockerfile
# Stage 1 -- build
FROM node:22-alpine AS builder
WORKDIR /app
COPY mydocs-ui/package.json mydocs-ui/package-lock.json ./
RUN npm ci
COPY mydocs-ui/ .
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_ENTRA_CLIENT_ID=""
ARG VITE_ENTRA_AUTHORITY=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_ENTRA_CLIENT_ID=${VITE_ENTRA_CLIENT_ID}
ENV VITE_ENTRA_AUTHORITY=${VITE_ENTRA_AUTHORITY}
RUN npm run build

# Stage 2 -- serve
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

| Property | Value |
|----------|-------|
| Base image (runtime) | `nginx:1.27-alpine` |
| Exposed port | `80` |
| Static files | `/usr/share/nginx/html` |
| Health check | `GET /` returns `200` |
| Build arg | `VITE_API_BASE_URL` (default `/api/v1`) |
| Build arg | `VITE_ENTRA_CLIENT_ID` -- Entra ID app registration client ID (baked into SPA at build time) |
| Build arg | `VITE_ENTRA_AUTHORITY` -- Entra ID authority URL, e.g. `https://login.microsoftonline.com/<tenant-id>` |

### 2.3 Nginx Configuration (`deploy/nginx.conf`)

Nginx serves the Vue SPA and proxies `/api` and `/health` to the backend container.

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Reverse-proxy API to backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 100M;
    }

    location /health {
        proxy_pass http://backend:8000;
    }
}
```

`client_max_body_size 100M` allows large document uploads. The upstream hostname `backend` is resolved via Docker Compose service name or Kubernetes service DNS.

---

## 3. Storage

All file storage (managed documents, uploads, config) is externalised from the container filesystem.

| Path inside container | Purpose | Docker Compose | Kubernetes |
|-----------------------|---------|----------------|------------|
| `/app/data` | Managed files, uploads | Bind mount to host directory | `PersistentVolumeClaim` |
| `/app/config` | `parser.yml` and other config | Bind mount or baked into image | `ConfigMap` mount |

### 3.1 Docker Compose Storage

A host directory (e.g. `./data`) is bind-mounted into the backend container:

```yaml
volumes:
  - ./data:/app/data
  - ./config:/app/config
```

This makes files directly accessible on the host for debugging and backup.

### 3.2 Kubernetes Storage

A `PersistentVolumeClaim` provides durable storage independent of pod lifecycle:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mydocs-data
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
```

The PVC is mounted at `/app/data` in the backend pod. The storage class is left to the cluster default; override with `storageClassName` as needed.

For configuration, a `ConfigMap` holds `parser.yml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mydocs-config
data:
  parser.yml: |
    azure_di_model: prebuilt-layout
    ...
```

---

## 4. Docker Compose Deployment

### 4.1 Compose File (`docker-compose.yml`)

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      DATA_FOLDER: /app/data
      CONFIG_ROOT: /app/config
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  ui:
    build:
      context: .
      dockerfile: Dockerfile.ui
    ports:
      - "80:80"
    depends_on:
      backend:
        condition: service_healthy
```

### 4.2 Environment

All secrets and configuration are supplied via `.env` file (not committed to git). Required variables:

| Variable | Example |
|----------|---------|
| `MONGO_URL` | `mongodb+srv://cluster.mongodb.net` |
| `MONGO_USER` | `mydocs_user` |
| `MONGO_PASSWORD` | `***` |
| `MONGO_DB_NAME` | `mydocs` |
| `AZURE_DI_ENDPOINT` | `https://mydi.cognitiveservices.azure.com` |
| `AZURE_DI_API_KEY` | `***` |
| `AZURE_OPENAI_API_KEY` | `***` |
| `AZURE_OPENAI_API_BASE` | `https://myoai.openai.azure.com` |
| `ENTRA_TENANT_ID` | (empty to disable auth in local dev) |
| `ENTRA_CLIENT_ID` | Entra ID app registration client ID |

### 4.3 Usage

```bash
# Start all services
docker compose up -d

# Rebuild after code changes
docker compose up -d --build

# View logs
docker compose logs -f backend

# Stop
docker compose down
```

---

## 5. Kubernetes Deployment

Kubernetes manifests use a **Kustomize base + overlays** pattern. The base contains cloud-agnostic manifests with generic image references. Each deployment target adds an overlay that customizes images, ingress, TLS, and secrets for its environment.

```
deploy/k8s/
  base/                         # Cloud-agnostic manifests
    kustomization.yaml
    namespace.yml, configmap.yml, pvc.yml, ...
    secret.yml.example          # Template (not applied by Kustomize)
  overlays/
    self-hosted/                # Manual deploy to any K8s cluster
      kustomization.yaml
      secret.yml                # User-created (gitignored)
    azure/                      # CI/CD deploy to Azure AKS
      kustomization.yaml
      ingress-patch.yml         # TLS + cert-manager
```

### 5.1 Deployment Targets

| Target | How to deploy | Images from |
|--------|--------------|-------------|
| **Self-hosted** | `kubectl apply -k deploy/k8s/overlays/self-hosted/` | Any registry |
| **Azure AKS** | Push to `azure-deployment` branch (CI/CD) | Azure Container Registry |
| **Future targets** | Add new overlay + workflow | Target-specific registry |

### 5.2 Base Manifests

The base contains all resources common across deployment targets. Images use generic names (`mydocs-backend:latest`, `mydocs-ui:latest`) that Kustomize overlays or `kustomize edit set image` can transform.

#### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mydocs
```

#### Secret (template only)

A `secret.yml.example` file documents the required keys. It is **not** listed in `kustomization.yaml` — each overlay manages secrets independently (self-hosted: user-created file; CI/CD: created from GitHub Secrets).

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mydocs-secrets
  namespace: mydocs
type: Opaque
stringData:
  MONGO_URL: ""
  MONGO_USER: ""
  MONGO_PASSWORD: ""
  MONGO_DB_NAME: ""
  AZURE_DI_ENDPOINT: ""
  AZURE_DI_API_KEY: ""
  AZURE_OPENAI_API_KEY: ""
  AZURE_OPENAI_API_BASE: ""
  ENTRA_TENANT_ID: ""
  ENTRA_CLIENT_ID: ""
```

#### Backend Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: mydocs
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mydocs-backend
  template:
    metadata:
      labels:
        app: mydocs-backend
    spec:
      containers:
        - name: backend
          image: mydocs-backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: mydocs-secrets
          env:
            - name: DATA_FOLDER
              value: /app/data
            - name: CONFIG_ROOT
              value: /app/config
          volumeMounts:
            - name: data
              mountPath: /app/data
            - name: config
              mountPath: /app/config
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 512Mi
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: mydocs-data
        - name: config
          configMap:
            name: mydocs-config
```

#### UI Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ui
  namespace: mydocs
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mydocs-ui
  template:
    metadata:
      labels:
        app: mydocs-ui
    spec:
      containers:
        - name: ui
          image: mydocs-ui:latest
          ports:
            - containerPort: 80
          livenessProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 30
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 128Mi
```

#### Services

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: mydocs
spec:
  selector:
    app: mydocs-backend
  ports:
    - port: 8000
      targetPort: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: ui
  namespace: mydocs
spec:
  selector:
    app: mydocs-ui
  ports:
    - port: 80
      targetPort: 80
```

The backend service name `backend` matches the Nginx upstream in the UI container, so `/api/` requests are proxied correctly via Kubernetes DNS (`backend.mydocs.svc.cluster.local`).

#### Ingress (base)

The base ingress is minimal — no TLS. Cloud-specific overlays patch in TLS and annotations.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mydocs-ingress
  namespace: mydocs
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
spec:
  ingressClassName: nginx
  rules:
    - host: mydocs.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: ui
                port:
                  number: 80
```

### 5.3 Self-Hosted Overlay

For deploying to any Kubernetes cluster (on-prem, Minikube, k3s, etc.) without CI/CD.

```yaml
# deploy/k8s/overlays/self-hosted/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
  - secret.yml    # Create from ../../base/secret.yml.example
```

Deploy:

```bash
# 1. Create secret from template
cp deploy/k8s/base/secret.yml.example deploy/k8s/overlays/self-hosted/secret.yml
# Edit secret.yml with your values

# 2. (Optional) Set custom image registry
cd deploy/k8s/overlays/self-hosted
kustomize edit set image \
  mydocs-backend=your-registry/mydocs-backend:TAG \
  mydocs-ui=your-registry/mydocs-ui:TAG

# 3. Apply
kubectl apply -k deploy/k8s/overlays/self-hosted/
```

### 5.4 Azure AKS Overlay

Used by the CI/CD pipeline. Patches the base ingress with TLS and cert-manager.

```yaml
# deploy/k8s/overlays/azure/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
patches:
  - path: ingress-patch.yml
```

```yaml
# deploy/k8s/overlays/azure/ingress-patch.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mydocs-ingress
  namespace: mydocs
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - mydocs.example.com
      secretName: mydocs-tls
```

Images and secrets are set dynamically by CI/CD (see Section 8).

### 5.5 Adding a New Cloud Target

To add support for a new cloud (e.g., AWS EKS):

1. Create `deploy/k8s/overlays/aws/kustomization.yaml` referencing `../../base`.
2. Add any cloud-specific patches (e.g., ALB ingress annotations instead of nginx).
3. Create `.github/workflows/deploy-eks.yml` following the Azure workflow as a template — swap `az` commands for `aws` commands, ACR for ECR, etc.
4. Add a trigger branch (`aws-deployment`).

All traffic enters through the UI Nginx, which handles SPA routing and reverse-proxies `/api/` to the backend service. TLS termination happens at the Ingress controller (configured per-overlay).

---

## 6. Networking

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

| Route | Handler |
|-------|---------|
| `GET /` | Nginx serves `index.html` (SPA) |
| `GET /assets/*` | Nginx serves static build artifacts |
| `POST /api/v1/*` | Nginx proxies to backend:8000 |
| `GET /health` | Nginx proxies to backend:8000 |

---

## 7. File Layout

Files introduced by this spec:

```
├── .github/
│   └── workflows/
│       └── deploy-aks.yml              # CI/CD: build → ACR → AKS
├── Dockerfile.backend                  # Backend image build
├── Dockerfile.ui                       # UI image build (multi-stage with Nginx)
├── docker-compose.yml                  # Local / single-server deployment
├── deploy/
│   ├── nginx.conf                      # Nginx config for UI container
│   └── k8s/
│       ├── base/                       # Cloud-agnostic K8s manifests
│       │   ├── kustomization.yaml
│       │   ├── namespace.yml
│       │   ├── configmap.yml
│       │   ├── pvc.yml
│       │   ├── backend-deployment.yml
│       │   ├── backend-service.yml
│       │   ├── ui-deployment.yml
│       │   ├── ui-service.yml
│       │   ├── ingress.yml
│       │   └── secret.yml.example      # Template (not applied)
│       └── overlays/
│           ├── self-hosted/
│           │   ├── kustomization.yaml
│           │   ├── README.md
│           │   └── secret.yml          # User-created (gitignored)
│           └── azure/
│               ├── kustomization.yaml
│               └── ingress-patch.yml   # TLS + cert-manager
```

---

## 8. CI/CD Pipeline

Each cloud target gets its own GitHub Actions workflow and trigger branch. Workflows follow a common pattern: build images → push to registry → deploy via Kustomize overlay.

### 8.1 Multi-Target Strategy

| Target | Trigger Branch | Workflow | Overlay |
|--------|---------------|----------|---------|
| **Azure AKS** | `azure-deployment` | `deploy-aks.yml` | `deploy/k8s/overlays/azure/` |
| **AWS EKS** (future) | `aws-deployment` | `deploy-eks.yml` | `deploy/k8s/overlays/aws/` |
| **Self-hosted** | n/a (manual) | n/a | `deploy/k8s/overlays/self-hosted/` |

All workflows also support `workflow_dispatch` for manual one-off deploys with an optional image tag override.

### 8.2 Azure AKS Pipeline (`deploy-aks.yml`)

#### Trigger

- **Push** to the `azure-deployment` branch (builds **and** deploys).
- **Pull request** targeting the `azure-deployment` branch (builds only, no deploy).
- **Manual dispatch** with optional image tag.

#### Required Configuration

**GitHub Secrets** (set in repository Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Service principal or managed-identity client ID for Azure OIDC login |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `ENTRA_CLIENT_ID` | Entra ID app registration client ID (baked into UI at build time) |
| `ENTRA_AUTHORITY` | Entra ID authority URL, e.g. `https://login.microsoftonline.com/<tenant-id>` |
| `MONGO_URL`, `MONGO_USER`, `MONGO_PASSWORD`, `MONGO_DB_NAME` | MongoDB connection details |
| `AZURE_DI_ENDPOINT`, `AZURE_DI_API_KEY` | Azure Document Intelligence |
| `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_BASE` | Azure OpenAI |
| `MYDOCS_STORAGE_BACKEND` | `azure_blob` (recommended) or `local`. See Section 10. |
| `AZURE_STORAGE_ACCOUNT_NAME` | Azure Blob Storage account name (required when `MYDOCS_STORAGE_BACKEND=azure_blob`) |
| `AZURE_STORAGE_CONTAINER_NAME` | Blob container name (default: `managed`) |

**GitHub Variables** (set in repository Settings → Secrets and variables → Actions → Variables):

| Variable | Example | Description |
|----------|---------|-------------|
| `ACR_NAME` | `mydocsacr` | Azure Container Registry name (without `.azurecr.io`) |
| `AKS_CLUSTER_NAME` | `mydocs-aks` | AKS cluster name |
| `AKS_RESOURCE_GROUP` | `mydocs-rg` | Resource group containing the AKS cluster |

#### Pipeline Stages

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
│      VITE_ENTRA_* args)       │
└───────────┬───────────────────┘
            │ (push only, not on PR)
            ▼
┌───────────────────────────────┐
│  Deploy Job                   │
│  1. Azure Login (OIDC)        │
│  2. Get AKS credentials       │
│  3. Create K8s secret from    │
│     GitHub Secrets             │
│  4. kustomize edit set image  │
│     (stamp ACR + SHA tag)     │
│  5. kubectl apply -k overlay  │
│  6. Wait for rollout          │
└───────────────────────────────┘
```

The deploy job uses `kustomize edit set image` to stamp the correct ACR registry and commit SHA into the overlay, then applies with `kubectl apply -k`. Secrets are created idempotently from GitHub Secrets via `kubectl create secret ... --dry-run=client -o yaml | kubectl apply -f -`.

### 8.4 Manual / Local Builds

Images can also be built and tagged locally:

```bash
# Backend
docker build -f Dockerfile.backend -t mydocs-backend:$(git rev-parse --short HEAD) .

# UI (with OAuth build args)
docker build -f Dockerfile.ui \
  --build-arg VITE_ENTRA_CLIENT_ID=<client-id> \
  --build-arg VITE_ENTRA_AUTHORITY=https://login.microsoftonline.com/<tenant-id> \
  -t mydocs-ui:$(git rev-parse --short HEAD) .
```

---

## 9. Authentication

Authentication is implemented using **Microsoft Entra ID** (Azure AD) with an OAuth 2.0 / OpenID Connect flow.

### 9.1 Architecture

```
┌──────────┐     MSAL redirect     ┌─────────────────┐
│  Browser  │ ◄──────────────────► │  Entra ID       │
│  (Vue SPA)│    access_token       │  (login.ms.com) │
└─────┬─────┘                       └─────────────────┘
      │ Authorization: Bearer <token>
      ▼
┌─────────────┐
│  Backend    │ ── validates JWT signature via Entra JWKS
│  (FastAPI)  │
└─────────────┘
```

1. The **Vue UI** uses `@azure/msal-browser` to perform a redirect-based login against Entra ID and obtain an access token.
2. Every API request includes the token in the `Authorization: Bearer <token>` header.
3. The **FastAPI backend** validates the JWT signature, audience, issuer, and expiry using Entra's public JWKS keys.
4. The `/health` endpoint remains **unauthenticated** so Kubernetes probes work without tokens.

### 9.2 Local Development

When `ENTRA_TENANT_ID` is **unset or empty**, the backend skips token validation entirely and returns a stub user (`local-dev`). On the frontend, the Vue Router `beforeEach` guard checks `VITE_ENTRA_CLIENT_ID` — when empty, it bypasses the auth guard entirely (no redirect to `/login`, no authenticated-user check). This allows the application to run without any Entra ID configuration during local development.

### 9.3 Configuration

| Layer | Variable | Description |
|-------|----------|-------------|
| Backend (env) | `ENTRA_TENANT_ID` | Azure AD tenant ID. Empty = auth disabled. |
| Backend (env) | `ENTRA_CLIENT_ID` | App registration client ID (audience for token validation). |
| Backend (env) | `ENTRA_ISSUER` | (Optional) Token issuer URL. Defaults to `https://login.microsoftonline.com/{tenant_id}/v2.0`. |
| UI (build arg) | `VITE_ENTRA_CLIENT_ID` | Same client ID, baked into the SPA at build time. |
| UI (build arg) | `VITE_ENTRA_AUTHORITY` | Authority URL, e.g. `https://login.microsoftonline.com/<tenant-id>`. |

---

## 10. Storage Modes × Deployment Targets

The application has two orthogonal storage concepts:

- **Storage mode** (`managed` vs `external`) — whether the file is copied into managed storage or stays at its original path.
- **Storage backend** (`local` vs `azure_blob`) — where managed storage physically lives.

Different deployment targets have different constraints on which combinations are practical.

### 10.1 Compatibility Matrix

| Storage Backend | Storage Mode | Docker Compose | Self-hosted K8s | Azure AKS |
|-----------------|-------------|----------------|-----------------|-----------|
| `local` | managed | Best fit. Bind-mount gives host access for debugging. | Works with `ReadWriteOnce` PVC. **Limits backend to 1 replica.** | Works but PVC-bound. Not recommended — use `azure_blob`. |
| `local` | external | Works if external paths are bind-mounted into the container. | Requires additional volume mounts for external paths. Must be configured per-cluster. | Impractical — external paths from other machines aren't accessible inside AKS pods. |
| `azure_blob` | managed | Works. Files go to Azure Blob — no local data volume needed for managed files. Config and DI cache still use local volume. | Eliminates PVC scaling limitation. **Backend scales to multiple replicas.** Config volume still needed. | **Recommended.** Uses managed identity. Eliminates PVC for file storage. Scales horizontally. |
| `azure_blob` | external | External files remain local. Sidecars written locally next to originals. Blob backend only used for managed sidecar storage during migration. | Same as Docker Compose — external paths need volume mounts. | Not practical. External paths not accessible from AKS pods. |

### 10.2 Recommended Configurations

| Deployment Target | Recommended Backend | Notes |
|-------------------|-------------------|-------|
| **Docker Compose** (local dev) | `local` | Simplest. No cloud credentials needed. Both storage modes work. |
| **Docker Compose** (staging) | `azure_blob` | Mirrors production. Use connection string or Azurite emulator. |
| **Self-hosted K8s** (single replica) | `local` | PVC is sufficient. Simple to operate. |
| **Self-hosted K8s** (multi-replica) | `azure_blob` | Avoids `ReadWriteMany` PVC requirement. |
| **Azure AKS** | `azure_blob` | Native fit. Uses managed identity. No PVC for files. |

### 10.3 External Mode Limitations in Kubernetes

External storage mode (`storage_mode: external`) assumes the backend process can read files at their original filesystem paths. This works in Docker Compose (with bind mounts) but has significant limitations in Kubernetes:

- **Original paths must be accessible** from inside the pod via additional volume mounts (NFS, hostPath, Azure Files, etc.).
- **K8s manifests do not include** external path volume mounts — operators must add them manually.
- **Not supported in CI/CD deployments** (Azure AKS) — use managed mode instead.

For Kubernetes deployments, the recommended workflow is:
1. Ingest files via the **upload endpoint** (always uses managed mode) or the **ingest endpoint** with `storage_mode: managed`.
2. If migrating from a local deployment that used external mode, use `sync migrate` to move files to managed storage first.

### 10.4 PVC Requirements by Backend

| Backend | PVC at `/app/data` | Purpose |
|---------|-------------------|---------|
| `local` | **Required** | Managed files, uploads, DI cache, sidecars |
| `azure_blob` | **Optional but recommended** | DI cache files (`.di.json`), uploads staging area, config |

When using `azure_blob`, the PVC can be smaller (e.g. 2Gi instead of 10Gi) since managed files live in Blob Storage. The PVC is still useful for:
- Temporary upload staging (`DATA_FOLDER/uploads/`)
- DI cache files written during parsing (`.di.json` alongside managed files — on local backend these go to disk, on `azure_blob` they are not persisted unless explicitly handled)
- Configuration files mounted via ConfigMap

### 10.5 Migrating Between Backends

When changing deployment targets (e.g. Docker Compose → AKS), file storage may need to migrate between backends. Use the `sync migrate` command or API:

```bash
# CLI: migrate local → azure_blob
mydocs sync migrate --from local --to azure_blob

# API: build plan first, then execute
POST /api/v1/sync/migrate/plan   {"source_backend": "local", "target_backend": "azure_blob"}
POST /api/v1/sync/migrate/execute {"source_backend": "local", "target_backend": "azure_blob"}
```

Migration is storage-only — no database writes. After migration, rebuild the DB from the target backend's sidecars:

```bash
mydocs sync run --backend azure_blob
```

See [sync.md](sync.md) Section 4.4 for the full migration algorithm.

### 10.6 Azure AKS with Azure Blob Storage

When deploying to Azure AKS with the `azure_blob` backend, the following additional secrets are required:

| Secret | Description |
|--------|-------------|
| `MYDOCS_STORAGE_BACKEND` | Set to `azure_blob` |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name |
| `AZURE_STORAGE_CONTAINER_NAME` | Blob container name (default: `managed`) |

Authentication options (pick one):
- **Managed identity** (recommended): Set only `AZURE_STORAGE_ACCOUNT_NAME`. The AKS pod's workload identity authenticates via `DefaultAzureCredential`.
- **Account key**: Set `AZURE_STORAGE_ACCOUNT_KEY` in addition to account name.
- **Connection string**: Set `AZURE_STORAGE_CONNECTION_STRING` instead.

---

## 11. Scaling Considerations

| Component | Scalability Notes |
|-----------|-------------------|
| **UI** | Stateless -- scale horizontally without restriction. |
| **Backend** | Stateless for read operations. Write operations (file uploads) require `ReadWriteMany` PVC or shared storage (e.g. NFS, Azure Files) if replicas > 1 with `local` backend. With `azure_blob` backend, scales horizontally without PVC concerns. |
| **Storage** | `local` backend: PVC is `ReadWriteOnce` — limit to 1 replica or switch to `ReadWriteMany` storage class. `azure_blob` backend: no PVC scaling limitation — recommended for multi-replica deployments. |