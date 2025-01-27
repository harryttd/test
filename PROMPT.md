I'm taking an interactive k8s challenge for a job interview. Help me implement the following tasks step by step that I'm given:

# Description
Write a custom secondary scheduler.
We have X nodes. Over time we get new Pods.
Each pod has a priority annotation.

# Tasks:
- Setup a local k8s cluster with multiple nodes.
  - For example, https://minikube.sigs.k8s.io/docs/tutorials/multi_node/
- Write a scheduler
  - See https://sebgoa.medium.com/kubernetes-scheduling-in-python-3588f4928b13
- Assign the top X priority pods to nodes
- Preempt
- Gang-scheduling for jobs
- When a job with multiple pods is assigned, all of its pods should be scheduled together, or none should.
- Write some tests for this.

# Expected delivery:
- A script that sets up the scheduler on an existing k8s cluster, in a given namespace.

