# 101 · Plain Kubernetes Deployment

The same workload as [`../ocp/`](../ocp/), for any conformant Kubernetes
(Docker Desktop, kind, minikube, EKS/AKS/GKE). One question, one Job, one
exit code; the CronJob gives the continuous MOC sweep. CPU-only, model served
elsewhere (any OpenAI-compatible endpoint).

| OpenShift (`../ocp/`)                | Kubernetes (here)                                   |
|--------------------------------------|-----------------------------------------------------|
| `oc new-project agent-school`        | `base/namespace.yaml`                               |
| ImageStream + BuildConfig            | local `docker build`, or `build-job.yaml` (Kaniko)  |
| internal registry image reference    | `images:` in `base/kustomization.yaml`              |
| random UID injected by the platform  | `runAsUser: 1001` (the UBI image's non-root user)   |
| `rome/` overlay (Feast, MLflow, Kueue) | not ported: OpenShift AI services                 |

## 1. Namespace, identity, credentials

```bash
kubectl apply -k 101-moc-assistant/deploy/k8s/base
kubectl -n agent-school create secret generic llm-credentials \
  --from-literal=LLM_BASE_URL=https://your-endpoint/v1 \
  --from-literal=LLM_API_KEY=sk-... \
  --from-literal=LLM_MODEL=your-model
```

(Template: `../../../shared/manifests/ocp/secret-llm.example.yaml`; it is
plain Kubernetes. Never commit a filled-in copy.)

## 2. Build the image

**Single-node cluster sharing your local image store** (Docker Desktop's
Kubernetes; for kind, add `kind load docker-image noc-assistant:latest`):

```bash
cd 101-moc-assistant
docker build -f deploy/Containerfile -t noc-assistant:latest .
```

**Any cluster with a registry**: build and push locally, or in-cluster with
the Kaniko Job (`build-job.yaml`, the BuildConfig counterpart; its header
lists the two secrets it needs). Then point the manifests at the pushed image:

```bash
cd 101-moc-assistant/deploy/k8s/base
kustomize edit set image noc-assistant=<registry>/agent-school/noc-assistant:latest
```

and edit `image:` in `job-ask.yaml` the same way.

## 3. Run

```bash
kubectl create -f 101-moc-assistant/deploy/k8s/job-ask.yaml
kubectl -n agent-school logs -f job/$(kubectl -n agent-school get jobs -o name --sort-by=.metadata.creationTimestamp | tail -1 | cut -d/ -f2)
```

Continuous sweep (applied suspended so it costs nothing until enabled):

```bash
kubectl -n agent-school patch cronjob noc-sweep -p '{"spec":{"suspend":false}}'
```

## Notes

- The image bundles the mfgcore-prod dataset and runbooks, so the agent
  works without Feast. `feature-store-client` and `mlflow-tracking`
  ConfigMaps are optional; create them only if you run those services.
- Pod security: agent pods meet `restricted` (non-root, default seccomp, all
  capabilities dropped). The namespace enforces `baseline` only because the
  Kaniko build runs as root; see `base/namespace.yaml`.
