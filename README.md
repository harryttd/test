# Custom Kubernetes Priority Scheduler

A custom Kubernetes scheduler implementation that handles pod scheduling based on priority annotations with support for preemption.

## Current Implementation Status

### Completed Features
- ✅ Basic scheduler deployment and RBAC setup
- ✅ Priority queue implementation for pod scheduling
- ✅ Basic node scoring and selection
- ✅ Pod priority annotation parsing
- ✅ Node capacity limits for test pods
- ✅ Basic preemption framework
- ✅ Basic bash scheduler deployment script. (please see .`/deploy-scheduler.sh`)


### Not Yet Implemented
- ❌ Gang-scheduling
- ❌ Priority updates handling
- ❌ Comprehensive test suite
- ❌ Performance testing

## Testing
Currently using test pods with different priority levels (40-200) to verify scheduling behavior.

### Test Files
- `k8s/test-pods.yaml`: Basic two-pod test setup
- `k8s/test-multiple-pods.yaml`: Extended test with multiple priority levels

## Next Steps
1. Implement gang-scheduling
2. Add comprehensive test suite
3. Add performance tests
4. Create Helm chart with configurable values:
   - Max pods per node
   - Scheduler name
   - Resource limits/requests
   - Priority thresholds
   - Namespace configuration
   - RBAC settings

## Development Setup

### Prerequisites
- Minikube with multiple nodes
- Python 3.8+
- kubectl configured for your cluster

### Quick Start
1. Build the scheduler:
```bash
docker build -t localhost:5000/custom-scheduler .
docker push localhost:5000/custom-scheduler
# Restart scheduler `kubectl -n kube-system delete pod -l app=custom-scheduler --force --grace-period=0`
```

2. Deploy the scheduler:
```bash
kubectl apply -f k8s/scheduler-deployment.yaml
```

3. Run test pods:
```bash
kubectl apply -f k8s/test-multiple-pods.yaml
```

### Monitoring
Watch scheduler logs:
```bash
kubectl -n kube-system logs -f -l app=custom-scheduler
```
