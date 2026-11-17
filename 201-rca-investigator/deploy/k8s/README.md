# 201 · Plain Kubernetes Deployment

The same workload as [`../ocp/`](../ocp/), for any conformant Kubernetes:
the RAG skill backend runs as a Deployment + Service, and each RCA is a Job.
See [101's Kubernetes README](../../../101-moc-assistant/deploy/k8s/README.md)
for how this maps onto the OpenShift manifests.

## 1. Namespace and credentials (from 101)

```bash
kubectl apply -k 101-moc-assistant/deploy/k8s/base
```

The `llm-credentials` Secret is shared; create it once as in 101's README.
201 also reads `LLM_MODEL_SMALL` / `LLM_MODEL_LARGE` if present.

## 2. Build the image (from the repo root: it bundles 101's dataset)

**Single-node cluster sharing your local image store** (Docker Desktop; for
kind add `kind load docker-image rca-investigator:latest`):

```bash
docker build -f 201-rca-investigator/deploy/Containerfile -t rca-investigator:latest .
```

**Any cluster with a registry**: push, or build in-cluster with
`build-job.yaml` (Kaniko), then
`kustomize edit set image rca-investigator=<registry>/agent-school/rca-investigator:latest`
in `base/`, and edit `image:` in `job-rca.yaml`.

## 3. Run

```bash
kubectl apply -k 201-rca-investigator/deploy/k8s/base
kubectl -n agent-school rollout status deploy/rca-rag
kubectl create -f 201-rca-investigator/deploy/k8s/job-rca.yaml
kubectl -n agent-school logs -f job/$(kubectl -n agent-school get jobs -o name --sort-by=.metadata.creationTimestamp | tail -1 | cut -d/ -f2)
```

The `rome/` overlay (LLM-as-judge, MLflow RBAC) targets OpenShift AI and is
not ported.
