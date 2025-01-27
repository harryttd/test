#!/bin/bash

# Default values
NAMESPACE="kube-system"
IMAGE_REGISTRY="localhost:5000"

# Help message
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Deploy the custom scheduler to a Kubernetes cluster"
    echo
    echo "Options:"
    echo "  -n, --namespace NAME    Deploy to namespace NAME (default: kube-system)"
    echo "  -r, --registry URL      Use container registry URL (default: localhost:5000)"
    echo "  -h, --help             Show this help message"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -r|--registry)
            IMAGE_REGISTRY="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

echo "Deploying custom scheduler to namespace: $NAMESPACE"

# Ensure namespace exists
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Build and push the scheduler image
echo "Building scheduler image..."
cd scheduler
docker build -t "$IMAGE_REGISTRY/custom-scheduler" .
docker push "$IMAGE_REGISTRY/custom-scheduler"

# Update deployment namespace in YAML
cd ../
echo "Updating deployment configuration..."
sed "s/namespace: kube-system/namespace: $NAMESPACE/" k8s/scheduler-deployment.yaml > scheduler-deployment-temp.yaml

# Deploy the scheduler
echo "Deploying scheduler..."
kubectl apply -f scheduler-deployment-temp.yaml

# Clean up temporary file
rm scheduler-deployment-temp.yaml

# Wait for deployment
echo "Waiting for scheduler deployment to be ready..."
kubectl rollout status deployment/custom-scheduler -n "$NAMESPACE"

echo "Deployment complete! To view scheduler logs:"
echo "kubectl -n $NAMESPACE logs -f -l app=custom-scheduler"
