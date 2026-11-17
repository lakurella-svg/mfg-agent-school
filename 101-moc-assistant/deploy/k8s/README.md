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
| `rome/` overlay (Feast, MLflow, Kueue) | not ported: AI platform services                 |

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

**Running on Claude instead.** The same Secret selects the Anthropic path:
the agent then calls Claude through the Anthropic SDK (no `LLM_BASE_URL`).
It needs an API key from the Claude Console (console.anthropic.com); a
claude.ai chat subscription does not include API access.

```bash
kubectl -n agent-school create secret generic llm-credentials \
  --from-literal=LLM_PROVIDER=anthropic \
  --from-literal=LLM_MODEL=claude-opus-5-5 \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-...
```

Optional `LLM_EFFORT` (`low` / `medium` / `high`; default `medium`). The pod
needs outbound HTTPS to `api.anthropic.com`.

## 2. Build the image

**Local cluster, no registry** (Docker Desktop, kind):

```bash
cd 101-moc-assistant
docker build -f deploy/Containerfile -t moc-assistant:latest .
```

Docker Desktop's **kubeadm** cluster sees that image directly. Its **kind**
cluster (node `desktop-control-plane`) and standalone kind keep a separate
image store, so load it into the node. Standalone kind:
`kind load docker-image moc-assistant:latest`. Docker Desktop kind (from
Git Bash, `export MSYS_NO_PATHCONV=1` first), through a temporary node pod:

```bash
kubectl debug node/desktop-control-plane -n default --profile=sysadmin --image=busybox:1.36 -- sleep 1800
P=$(kubectl get pods -n default -o name | grep node-debugger | head -1)
docker save moc-assistant:latest | kubectl exec -i -n default $P -- chroot /host ctr -n k8s.io images import -
kubectl delete -n default $P
```

**Any cluster with a registry**: build and push locally, or in-cluster with
the Kaniko Job (`build-job.yaml`, the BuildConfig counterpart; its header
lists the two secrets it needs). Then point the manifests at the pushed image:

```bash
cd 101-moc-assistant/deploy/k8s/base
kustomize edit set image moc-assistant=<registry>/agent-school/moc-assistant:latest
```

and edit `image:` in `job-ask.yaml` the same way.

## 3. Run

```bash
kubectl create -f 101-moc-assistant/deploy/k8s/job-ask.yaml
kubectl -n agent-school logs -f job/$(kubectl -n agent-school get jobs -o name --sort-by=.metadata.creationTimestamp | tail -1 | cut -d/ -f2)
```

Continuous sweep (applied suspended so it costs nothing until enabled):

```bash
kubectl -n agent-school patch cronjob moc-sweep -p '{"spec":{"suspend":false}}'
```

## Notes

- The image bundles the mfgcore-prod dataset and runbooks, so the agent
  works without Feast. `feature-store-client` and `mlflow-tracking`
  ConfigMaps are optional; create them only if you run those services.
- Pod security: agent pods meet `restricted` (non-root, default seccomp, all
  capabilities dropped). The namespace enforces `baseline` only because the
  Kaniko build runs as root; see `base/namespace.yaml`.
