# Self-Hosted Kubernetes Deployment

Deploy MyDocs to any Kubernetes cluster (on-prem, Minikube, k3s, etc.).

## Prerequisites

- `kubectl` configured to connect to your cluster
- An Nginx Ingress Controller installed (or adjust `ingressClassName` in the base)
- A container registry accessible from your cluster with the `mydocs-backend` and `mydocs-ui` images

## Setup

1. **Build and push images** to your registry:

   ```bash
   TAG=$(git rev-parse --short HEAD)

   docker build -f Dockerfile.backend -t your-registry/mydocs-backend:$TAG .
   docker build -f Dockerfile.ui -t your-registry/mydocs-ui:$TAG .

   docker push your-registry/mydocs-backend:$TAG
   docker push your-registry/mydocs-ui:$TAG
   ```

2. **Create the secrets file** from the template:

   ```bash
   cp ../../base/secret.yml.example secret.yml
   ```

   Edit `secret.yml` and fill in your values (MongoDB credentials, API keys, etc.).

3. **Set your image references** (if using a custom registry):

   ```bash
   cd deploy/k8s/overlays/self-hosted
   kustomize edit set image \
     mydocs-backend=your-registry/mydocs-backend:$TAG \
     mydocs-ui=your-registry/mydocs-ui:$TAG
   ```

   Or, if your images are available as `mydocs-backend:latest` and `mydocs-ui:latest`
   (e.g., loaded via `docker save`/`docker load`), skip this step.

4. **Deploy**:

   ```bash
   kubectl apply -k deploy/k8s/overlays/self-hosted/
   ```

5. **Verify**:

   ```bash
   kubectl get pods -n mydocs
   kubectl rollout status deployment/backend -n mydocs
   kubectl rollout status deployment/ui -n mydocs
   ```

## Customization

- **Hostname**: Edit `base/ingress.yml` or add an ingress patch in this overlay.
- **TLS**: Add a TLS section to the ingress (see `overlays/azure/ingress-patch.yml` for an example).
- **Storage class**: Override the PVC `storageClassName` via a Kustomize patch.
- **Replicas**: Add a patch to increase backend/UI replica counts.

## Updating

To roll out a new version:

```bash
TAG=$(git rev-parse --short HEAD)

# Build & push new images
docker build -f Dockerfile.backend -t your-registry/mydocs-backend:$TAG .
docker build -f Dockerfile.ui -t your-registry/mydocs-ui:$TAG .
docker push your-registry/mydocs-backend:$TAG
docker push your-registry/mydocs-ui:$TAG

# Update and apply
cd deploy/k8s/overlays/self-hosted
kustomize edit set image \
  mydocs-backend=your-registry/mydocs-backend:$TAG \
  mydocs-ui=your-registry/mydocs-ui:$TAG
kubectl apply -k .
```
