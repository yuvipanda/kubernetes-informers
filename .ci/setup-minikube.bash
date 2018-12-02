#!/bin/bash
set -euo pipefail
export CHANGE_MINIKUBE_NONE_USER=true
export KUBERNETES_VERSION=v1.12.0
export MINIKUBE_VERSION=v0.30.0

# Make root mounted as rshared to fix kube-dns issues.
sudo mount --make-rshared /

# Download kubectl, which is a requirement for using minikube.
curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/${KUBERNETES_VERSION}/bin/linux/amd64/kubectl
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Download minikube.
curl -Lo minikube https://storage.googleapis.com/minikube/releases/${MINIKUBE_VERSION}/minikube-linux-amd64
chmod +x minikube
sudo mv minikube /usr/local/bin/

# Start minikube
sudo minikube start --vm-driver=none --bootstrapper=kubeadm --kubernetes-version=${KUBERNETES_VERSION}

# Fix the kubectl context, as it's often stale.
minikube update-context

# Wait for Kubernetes to be up and ready.
JSONPATH='{range .items[*]}{@.metadata.name}:{range @.status.conditions[*]}{@.type}={@.status};{end}{end}'; until kubectl get nodes -o jsonpath="$JSONPATH" 2>&1 | grep -q "Ready=True"; do sleep 1; done

# Wait for kube-dns to be ready
kubectl --namespace=kube-system rollout status -w deployment/kube-dns