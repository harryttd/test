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

### In Progress
- 🚧 Preemption Logic
  - Currently has basic structure but priority handling needs improvement
  - Lower priority pods can still get scheduled before higher priority ones in some cases
  - Need to implement proper priority queue ordering during node assignment
- 🚧 Resource tracking and allocation

### Not Yet Implemented
- ❌ Gang-scheduling
- ❌ Priority updates handling
- ❌ Comprehensive test suite
- ❌ Performance testing

## Current Limitations
1. Priority Handling: While we parse priority annotations, the scheduler may not always respect priorities strictly during node assignment
2. Preemption: Basic framework exists but needs improvement to properly handle priority-based evictions
3. Resource Management: Basic resource checking implemented but needs refinement

## Testing
Currently using test pods with different priority levels (40-200) to verify scheduling behavior.

### Test Files
- `k8s/test-pods.yaml`: Basic two-pod test setup
- `k8s/test-multiple-pods.yaml`: Extended test with multiple priority levels

## Next Steps
1. Fix priority handling to ensure strict priority ordering
2. Improve preemption logic
3. Implement gang-scheduling
4. Add comprehensive test suite
5. Add performance tests

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

## Contributing
Please see SPEC.md for detailed technical specifications and requirements.
