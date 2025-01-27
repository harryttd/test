from kubernetes import client, config, watch
import logging

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

    def run(self):
        w = watch.Watch()
        for event in w.stream(self.v1.list_pod_for_all_namespaces, timeout_seconds=0):
            pod = event['object']
            if pod.spec.scheduler_name == self.scheduler_name and \
               not pod.spec.node_name and \
               pod.status.phase == "Pending":
                try:
                    self.schedule_pod(pod)
                except Exception as e:
                    logger.error(f"Error scheduling pod {pod.metadata.name}: {e}")

    def schedule_pod(self, pod):
        # Get pod priority from annotation
        priority = int(pod.metadata.annotations.get(
            'scheduler.alpha.kubernetes.io/priority', '0'))

        # Get list of nodes
        nodes = self.v1.list_node().items

        # Simple scheduling - just pick first Ready node
        # TODO: Implement proper priority and preemption logic
        for node in nodes:
            if self.is_node_ready(node):
                self.bind_pod(pod, node.metadata.name)
                logger.info(f"Scheduled pod {pod.metadata.name} on node {node.metadata.name}")
                return

        logger.warning(f"No suitable node found for pod {pod.metadata.name}")

    def is_node_ready(self, node):
        for condition in node.status.conditions:
            if condition.type == "Ready" and condition.status == "True":
                return True
        return False

    def bind_pod(self, pod, node_name):
        binding = client.V1Binding(
            metadata=client.V1ObjectMeta(
                name=pod.metadata.name,
                namespace=pod.metadata.namespace
            ),
            target=client.V1ObjectReference(
                api_version="v1",
                kind="Node",
                name=node_name
            )
        )

        self.v1.create_namespaced_binding(
            name=pod.metadata.name,
            namespace=pod.metadata.namespace,
            body=binding
        )

if __name__ == "__main__":
    scheduler = PriorityScheduler()
    scheduler.run()
