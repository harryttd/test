from kubernetes import client, config, watch
import logging
import traceback
from queue import PriorityQueue
from dataclasses import dataclass
from typing import Optional
import time
import re

@dataclass(order=True)
class PodQueueItem:
    priority: int
    timestamp: float  # For FIFO ordering of same-priority pods
    pod: Optional[client.V1Pod] = None

    def __init__(self, pod: client.V1Pod):
        self.pod = pod
        self.priority = int(pod.metadata.annotations.get(
            "scheduler.alpha.kubernetes.io/priority", "0"))
        self.timestamp = time.time()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriorityScheduler:
    def __init__(self):
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()

        self.v1 = client.CoreV1Api()
        self.scheduler_name = "custom-scheduler"
        self.pod_queue = PriorityQueue()
        self.max_pods_per_node = 2  # Configure this as needed

    def run(self):
        logger.info("Starting custom scheduler...")
        w = watch.Watch()
        try:
            for event in w.stream(
                self.v1.list_pod_for_all_namespaces, timeout_seconds=0
            ):
                pod = event["object"]
                logger.info(f"Received event type: {event['type']} for pod: {pod.metadata.name}")

                if event["type"] == "DELETED":
                    logger.info(f"Processing DELETE event for pod: {pod.metadata.name}")
                    self.remove_pod_from_queue(pod)
                    # Process queue after pod deletion in case lower priority pods can now be scheduled
                    self.process_queue()
                elif event["type"] in ["ADDED", "MODIFIED"]:
                    # logger.info(f"Processing {event['type']} event for pod: {pod.metadata.name}")
                    if (
                        pod.spec.scheduler_name == self.scheduler_name
                        and not pod.spec.node_name
                        and pod.status.phase == "Pending"
                    ):
                        try:
                            logger.info(
                                f"Attempting to schedule pod: {pod.metadata.namespace}/{pod.metadata.name}"
                            )
                            self.schedule_pod(pod)
                        except Exception as e:
                            logger.error(
                                f"Error scheduling pod {pod.metadata.namespace}/{pod.metadata.name}: {e}\n"
                                f"Stack trace:\n{traceback.format_exc()}"
                            )
        except Exception as e:
            logger.error(f"Watch failed: {e}\nStack trace:\n{traceback.format_exc()}")
            raise

    def schedule_pod(self, pod):
        if pod.spec.node_name:
            logger.info(f"Pod {pod.metadata.name} is already scheduled to {pod.spec.node_name}")
            return

        # Add pod to priority queue instead of immediate scheduling
        queue_item = PodQueueItem(pod)
        logger.info(f"Processing pod {pod.metadata.name} with priority {queue_item.priority}")
        self.pod_queue.put((-queue_item.priority, queue_item))  # Negative for highest-first
        self.process_queue()

    def process_queue(self):
        """Process pods in priority order"""
        # Create a list of all pods in queue for logging and processing
        temp_queue = PriorityQueue()
        pods_to_process = []
        
        # Get all pods from queue and sort by priority
        while not self.pod_queue.empty():
            priority, queue_item = self.pod_queue.get()
            pods_to_process.append((priority, queue_item))
            
        # Sort by priority (highest first) and timestamp
        pods_to_process.sort(key=lambda x: (x[0], -x[1].timestamp))
        
        logger.info(f"Processing queue with {len(pods_to_process)} pods")
        for pod_info in [f"{item[1].pod.metadata.name} (priority: {-item[0]})" for item in pods_to_process]:
            logger.info(f"Queue contains: {pod_info}")
            
        # Process pods in priority order
        for priority, queue_item in pods_to_process:
            pod = queue_item.pod
            nodes = self.v1.list_node().items
            best_node = self.select_best_node(nodes, pod)
            
            if best_node:
                try:
                    self.bind_pod(pod, best_node.metadata.name)
                    logger.info(f"Successfully scheduled pod {pod.metadata.name} on node {best_node.metadata.name}")
                    continue  # Skip putting back in queue
                except client.rest.ApiException as e:
                    if e.status == 409:
                        logger.info(f"Pod {pod.metadata.name} was scheduled by another scheduler")
                        continue  # Skip putting back in queue
                    else:
                        raise
                        
            # Try preemption if direct scheduling failed
            preemption_node = self.find_preemption_node(nodes, pod)
            if preemption_node:
                logger.info(f"Found node {preemption_node.metadata.name} for preemption to schedule {pod.metadata.name}")
                self.perform_preemption(preemption_node, pod)
                try:
                    self.bind_pod(pod, preemption_node.metadata.name)
                    logger.info(f"Successfully scheduled pod {pod.metadata.name} on node {preemption_node.metadata.name} after preemption")
                    continue  # Skip putting back in queue
                except client.rest.ApiException as e:
                    logger.error(f"Failed to schedule pod after preemption: {e}")
            
            # If we get here, we couldn't schedule the pod
            logger.warning(f"Could not schedule pod {pod.metadata.name} - returning to queue")
            temp_queue.put((priority, queue_item))
            
        # Restore unscheduled pods to the queue
        self.pod_queue = temp_queue

    def select_best_node(self, nodes, pod):
        """Score nodes and select best one for the pod"""
        best_score = float('-inf')
        best_node = None

        for node in nodes:
            if not self.is_node_ready(node):
                continue

            score = self.score_node(node, pod)
            if score > best_score:
                best_score = score
                best_node = node

        return best_node

    def parse_k8s_resource(self, value):
        """Convert Kubernetes resource values to base numeric values"""
        if not value:
            return 0

        # Handle CPU values like "100m" (millicores)
        if isinstance(value, str) and value.endswith('m'):
            return float(value[:-1]) / 1000

        # Handle memory values like "1Ki", "1Mi", "1Gi"
        if isinstance(value, str):
            match = re.match(r'^(\d+)(Ki|Mi|Gi)?$', value)
            if match:
                num = float(match.group(1))
                unit = match.group(2)
                if unit == 'Ki':
                    return num * 1024
                elif unit == 'Mi':
                    return num * 1024 * 1024
                elif unit == 'Gi':
                    return num * 1024 * 1024 * 1024

        return float(value)

    def get_node_pod_count(self, node_name):
        """Get number of pods currently on the node"""
        field_selector = f'spec.nodeName={node_name},status.phase!=Failed,status.phase!=Succeeded'
        pods = self.v1.list_pod_for_all_namespaces(field_selector=field_selector).items
        # Only count pods that have 'priority' in their name
        priority_pods = [pod for pod in pods if 'priority' in pod.metadata.name.lower()]
        logger.info(f"Node {node_name} has {len(priority_pods)} priority test pods")
        return len(priority_pods)

    def score_node(self, node, pod):
        """Score a node for pod placement"""
        # Check pod count limit first
        current_pod_count = self.get_node_pod_count(node.metadata.name)
        if current_pod_count >= self.max_pods_per_node:
            logger.info(f"Node {node.metadata.name} at pod limit ({current_pod_count}/{self.max_pods_per_node})")
            return float('-inf')

        score = 0
        # Basic scoring based on available resources
        allocatable = node.status.allocatable
        if allocatable:
            cpu_alloc = self.parse_k8s_resource(allocatable.get('cpu', 0))
            mem_alloc = self.parse_k8s_resource(allocatable.get('memory', 0))
            # Normalize memory score by dividing by 1Gi to make it comparable to CPU
            score += cpu_alloc + (mem_alloc / (1024 * 1024 * 1024))

        return score

    def is_node_ready(self, node):
        for condition in node.status.conditions:
            if condition.type == "Ready" and condition.status == "True":
                return True
        return False

    def remove_pod_from_queue(self, pod_to_remove):
        """Remove a specific pod from the priority queue"""
        # Create a temporary queue
        temp_queue = PriorityQueue()
        removed = False
        queue_size = self.pod_queue.qsize()

        logger.info(f"Attempting to remove pod {pod_to_remove.metadata.name} from queue of size {queue_size}")

        ## FIX
        # Move all items except the one to remove
        while not self.pod_queue.empty():
            priority, queue_item = self.pod_queue.get()
            if (queue_item.pod.metadata.name != pod_to_remove.metadata.name or
                queue_item.pod.metadata.namespace != pod_to_remove.metadata.namespace):
                temp_queue.put((priority, queue_item))
            else:
                removed = True
                logger.info(f"Removed pod {pod_to_remove.metadata.name} from scheduling queue")

        # Restore the queue
        self.pod_queue = temp_queue
        return removed

    def find_lowest_priority_pod(self, nodes, incoming_priority):
        """Find the lowest priority pod across all nodes"""
        lowest_priority = incoming_priority
        lowest_pod = None
        lowest_pod_node = None

        for node in nodes:
            if not self.is_node_ready(node):
                continue

            field_selector = f'spec.nodeName={node.metadata.name},status.phase!=Failed,status.phase!=Succeeded'
            pods = self.v1.list_pod_for_all_namespaces(field_selector=field_selector).items
            priority_pods = [p for p in pods if 'priority' in p.metadata.name.lower()]

            for pod in priority_pods:
                pod_priority = int(pod.metadata.annotations.get("scheduler.alpha.kubernetes.io/priority", "0"))
                if pod_priority < lowest_priority:
                    lowest_priority = pod_priority
                    lowest_pod = pod
                    lowest_pod_node = node
                    logger.info(f"Found new lowest priority pod {pod.metadata.name} ({pod_priority}) on node {node.metadata.name}")

        return lowest_pod, lowest_pod_node

    def find_preemption_node(self, nodes, incoming_pod):
        """Find a node where we can preempt lower priority pods"""
        incoming_priority = int(incoming_pod.metadata.annotations.get("scheduler.alpha.kubernetes.io/priority", "0"))
        lowest_pod, node = self.find_lowest_priority_pod(nodes, incoming_priority)
        
        if lowest_pod:
            logger.info(f"Selected lowest priority pod {lowest_pod.metadata.name} on node {node.metadata.name} for preemption")
            return node

        return None

    def perform_preemption(self, node, incoming_pod):
        """Evict the lowest priority pod from the node"""
        incoming_priority = int(incoming_pod.metadata.annotations.get("scheduler.alpha.kubernetes.io/priority", "0"))
        lowest_pod, _ = self.find_lowest_priority_pod([node], incoming_priority)

        if lowest_pod:
            logger.info(f"Evicting lowest priority pod {lowest_pod.metadata.name}")
            try:
                self.v1.delete_namespaced_pod(
                    name=lowest_pod.metadata.name,
                    namespace=lowest_pod.metadata.namespace,
                    body=client.V1DeleteOptions(
                        grace_period_seconds=0,
                        propagation_policy='Foreground'
                    )
                )
                logger.info(f"Successfully evicted pod {lowest_pod.metadata.name}")
                # Wait a moment for the pod to be removed
                time.sleep(1)
            except client.rest.ApiException as e:
                logger.error(f"Failed to evict pod {lowest_pod.metadata.name}: {e}")

    def bind_pod(self, pod, node_name):
        target = client.V1ObjectReference(api_version="v1", kind="Node", name=node_name)

        meta = client.V1ObjectMeta(
            name=pod.metadata.name, namespace=pod.metadata.namespace
        )

        binding = client.V1Binding(metadata=meta, target=target)

        logger.info(f"Binding pod {pod.metadata.name} to node {node_name}")
        self.v1.create_namespaced_binding(
            namespace=pod.metadata.namespace,
            body=binding,
            # https://github.com/kubernetes-client/python/issues/825
            _preload_content=False
        )


if __name__ == "__main__":
    scheduler = PriorityScheduler()
    scheduler.run()
