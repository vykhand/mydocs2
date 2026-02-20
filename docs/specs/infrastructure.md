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

### 5.1 Namespace

All resources live in a dedicated namespace:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mydocs
```

### 5.2 Secret

Sensitive configuration stored in a Kubernetes Secret:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mydocs-secrets
  namespace: mydocs
type: Opaque
stringData:
  MONGO_URL: "mongodb+srv://cluster.mongodb.net"
  MONGO_USER: "mydocs_user"
  MONGO_PASSWORD: "***"
  MONGO_DB_NAME: "mydocs"
  AZURE_DI_ENDPOINT: "https://mydi.cognitiveservices.azure.com"
  AZURE_DI_API_KEY: "***"
  AZURE_OPENAI_API_KEY: "***"
  AZURE_OPENAI_API_BASE: "https://myoai.openai.azure.com"
  # Entra ID (Azure AD) — set these to enable backend JWT validation
  ENTRA_TENANT_ID: ""
  ENTRA_CLIENT_ID: ""
```

### 5.3 Backend Deployment

The image tag is a placeholder; CI/CD overwrites it via `kubectl set image` on each deploy.

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
          # Image tag is overwritten by CI/CD via `kubectl set image`
          image: YOUR_ACR.azurecr.io/mydocs-backend:latest
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

### 5.4 UI Deployment

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
          # Image tag is overwritten by CI/CD via `kubectl set image`
          image: YOUR_ACR.azurecr.io/mydocs-ui:latest
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

### 5.5 Services

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

### 5.6 Ingress

TLS is configured with a Kubernetes Secret (`mydocs-tls`). When cert-manager is installed in the cluster, uncomment the `cert-manager.io/cluster-issuer` annotation to enable automatic certificate provisioning.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mydocs-ingress
  namespace: mydocs
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    # Uncomment the line below if you use cert-manager for automatic TLS
    # cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - mydocs.example.com
      secretName: mydocs-tls
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

All traffic enters through the UI Nginx, which handles SPA routing and reverse-proxies `/api/` to the backend service. TLS termination happens at the Ingress controller.

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
│       └── deploy-aks.yml      # CI/CD: build → ACR → AKS
├── Dockerfile.backend          # Backend image build
├── Dockerfile.ui               # UI image build (multi-stage with Nginx)
├── docker-compose.yml          # Local / single-server deployment
├── deploy/
│   ├── nginx.conf              # Nginx config for UI container
│   └── k8s/
│       ├── namespace.yml
│       ├── secret.yml
│       ├── configmap.yml
│       ├── pvc.yml
│       ├── backend-deployment.yml
│       ├── backend-service.yml
│       ├── ui-deployment.yml
│       ├── ui-service.yml
│       └── ingress.yml
```

---

## 8. CI/CD Pipeline

Automated build and deployment is handled by a GitHub Actions workflow (`.github/workflows/deploy-aks.yml`). The pipeline targets **Azure Kubernetes Service (AKS)** with images stored in **Azure Container Registry (ACR)**.

### 8.1 Trigger

The workflow runs on:

- **Push** to the `azure-deployment` branch (builds **and** deploys).
- **Pull request** targeting the `azure-deployment` branch (builds only, no deploy).

### 8.2 Required Configuration

**GitHub Secrets** (set in repository Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Service principal or managed-identity client ID for Azure OIDC login |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `ENTRA_CLIENT_ID` | Entra ID app registration client ID (baked into UI at build time) |
| `ENTRA_AUTHORITY` | Entra ID authority URL, e.g. `https://login.microsoftonline.com/<tenant-id>` |

**GitHub Variables** (set in repository Settings → Secrets and variables → Actions → Variables):

| Variable | Example | Description |
|----------|---------|-------------|
| `ACR_NAME` | `mydocsacr` | Azure Container Registry name (without `.azurecr.io`) |
| `AKS_CLUSTER_NAME` | `mydocs-aks` | AKS cluster name |
| `AKS_RESOURCE_GROUP` | `mydocs-rg` | Resource group containing the AKS cluster |

### 8.3 Pipeline Stages

```
push to azure-deployment
        │
        ▼
┌───────────────────────────┐
│  Build Job                │
│  1. Checkout              │
│  2. Azure Login (OIDC)    │
│  3. ACR Login             │
│  4. Build & push backend  │
│     image (SHA + latest)  │
│  5. Build & push UI image │
│     (SHA + latest, with   │
│      VITE_ENTRA_* args)   │
└───────────┬───────────────┘
            │ (push only, not on PR)
            ▼
┌───────────────────────────┐
│  Deploy Job               │
│  1. Azure Login (OIDC)    │
│  2. Get AKS credentials   │
│  3. kubectl apply manifests│
│  4. kubectl set image     │
│     (backend + UI → SHA)  │
│  5. Wait for rollout      │
└───────────────────────────┘
```

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

When `ENTRA_TENANT_ID` is **unset or empty**, the backend skips token validation entirely and returns a stub user (`local-dev`). The UI will also skip the login redirect when `VITE_ENTRA_CLIENT_ID` is empty. This allows the application to run without any Entra ID configuration during local development.

### 9.3 Configuration

| Layer | Variable | Description |
|-------|----------|-------------|
| Backend (env) | `ENTRA_TENANT_ID` | Azure AD tenant ID. Empty = auth disabled. |
| Backend (env) | `ENTRA_CLIENT_ID` | App registration client ID (audience for token validation). |
| Backend (env) | `ENTRA_ISSUER` | (Optional) Token issuer URL. Defaults to `https://login.microsoftonline.com/{tenant_id}/v2.0`. |
| UI (build arg) | `VITE_ENTRA_CLIENT_ID` | Same client ID, baked into the SPA at build time. |
| UI (build arg) | `VITE_ENTRA_AUTHORITY` | Authority URL, e.g. `https://login.microsoftonline.com/<tenant-id>`. |

---

## 10. Scaling Considerations

| Component | Scalability Notes |
|-----------|-------------------|
| **UI** | Stateless -- scale horizontally without restriction. |
| **Backend** | Stateless for read operations. Write operations (file uploads) require `ReadWriteMany` PVC or shared storage (e.g. NFS, Azure Files) if replicas > 1. With `ReadWriteOnce`, limit to 1 replica or use a shared storage backend. |
| **Storage** | Local PVC is `ReadWriteOnce`. For multi-replica backends, switch to `ReadWriteMany`-capable storage class or migrate to a cloud storage backend (Azure Blob, S3 -- planned P1/P2). |