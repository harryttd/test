# Custom K8s Priority Scheduler Specification

## Overview
Implementation of a custom Kubernetes scheduler that handles pod scheduling based on priority annotations with support for gang-scheduling and preemption.

## Requirements

### 1. Development Environment
- Local Kubernetes cluster with multiple nodes using Minikube
- Minimum 2-3 worker nodes for testing
- Python environment for scheduler implementation

### 2. Scheduler Core Features
- Custom scheduler deployment in specified namespace
- Priority-based pod scheduling
- Support for priority annotation format: `scheduler.alpha.kubernetes.io/priority: "<integer>"`
- Node assignment based on pod priority ranking
- Preemption support for higher priority pods
- Gang-scheduling implementation

### 3. Detailed Specifications

#### Cluster Setup
- Minikube multi-node cluster
- Resource requirements:
  - Minimum 2 worker nodes
  - Sufficient CPU/Memory for testing multiple pods

#### Scheduler Implementation
- Python-based implementation
- Kubernetes client library integration
- Watch API implementation for pod events
- Priority queue management
- Node allocation strategy

#### Priority Handling
- Parse priority annotations from pods
- Maintain sorted priority queue
- Schedule highest priority pods first
- Support for priority updates

#### Preemption Logic
- Identify lower priority pods for eviction
- Safe pod eviction process
- Resource reallocation
- Preemption threshold configuration

#### Gang-scheduling
- Job grouping mechanism
- All-or-nothing scheduling policy
- Resource reservation system
- Job identification via labels/annotations

### 4. Testing Requirements
- Unit tests for core scheduling logic
- Integration tests for:
  - Priority scheduling
  - Preemption scenarios
  - Gang-scheduling
- Performance tests with multiple pods/nodes
- Edge case handling

### 5. Deliverables
- Setup script for scheduler deployment
  - Namespace creation
  - RBAC setup
  - Scheduler deployment
  - Configuration options
- Documentation
  - Setup instructions
  - Configuration guide
  - Testing procedures

### 6. Success Criteria
- Scheduler successfully deploys to specified namespace
- Priority-based scheduling works as expected
- Preemption correctly handles resource reallocation
- Gang-scheduling ensures atomic job scheduling
- All tests pass
- Setup script works on clean cluster

## Technical Constraints
- Compatible with Kubernetes 1.20+
- Python 3.8+ compatibility
- Minimal external dependencies
- RESTful API compliance
- Standard Kubernetes RBAC model
