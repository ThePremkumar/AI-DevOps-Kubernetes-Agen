import json
from loguru import logger
from typing import Dict, Any, List
from .executor import run_kubectl_command

class PodInspector:
    @staticmethod
    def inspect() -> Dict[str, Any]:
        """
        Gets status of pods across all namespaces and identifies unhealthy ones.
        """
        result = run_kubectl_command(["get", "pods", "-A", "-o", "json"])
        if not result["success"]:
            logger.warning(f"Failed to get pods: {result['stderr']}")
            return {"healthy": False, "error": result["stderr"], "problematic_pods": []}

        try:
            data = json.loads(result["stdout"])
            problematic_pods = []
            healthy = True

            unhealthy_statuses = {
                "CrashLoopBackOff", "ImagePullBackOff", "Pending", 
                "Error", "OOMKilled", "ContainerCreating"
            }

            for item in data.get("items", []):
                name = item["metadata"]["name"]
                namespace = item["metadata"]["namespace"]
                status_phase = item.get("status", {}).get("phase", "Unknown")
                
                # Check container statuses for waiting/terminated states
                container_statuses = item.get("status", {}).get("containerStatuses", [])
                pod_status = status_phase

                for cs in container_statuses:
                    state = cs.get("state", {})
                    waiting = state.get("waiting", {})
                    if waiting:
                        pod_status = waiting.get("reason", pod_status)
                    terminated = state.get("terminated", {})
                    if terminated:
                        pod_status = terminated.get("reason", pod_status)

                # Check if this pod status indicates a problem
                if pod_status in unhealthy_statuses or status_phase not in ("Running", "Succeeded"):
                    healthy = False
                    problematic_pods.append({
                        "name": name,
                        "namespace": namespace,
                        "status": pod_status,
                        "phase": status_phase
                    })

            return {
                "healthy": len(problematic_pods) == 0,
                "problematic_pods": problematic_pods,
                "total_pods_checked": len(data.get("items", []))
            }
        except Exception as e:
            logger.exception("Failed to parse pods json")
            return {"healthy": False, "error": f"Parse error: {str(e)}", "problematic_pods": []}


class LogsCollector:
    @staticmethod
    def collect(problematic_pods: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Fetches the last 50 lines of logs for the provided problematic pods.
        """
        logs = {}
        for pod in problematic_pods[:5]:  # Limit to top 5 pods to keep payload reasonable
            name = pod["name"]
            namespace = pod["namespace"]
            result = run_kubectl_command(["logs", name, "-n", namespace, "--tail=50"])
            if result["success"]:
                logs[f"{namespace}/{name}"] = result["stdout"]
            else:
                logs[f"{namespace}/{name}"] = f"Failed to retrieve logs: {result['stderr']}"
        return logs


class EventsAnalyzer:
    @staticmethod
    def analyze() -> List[Dict[str, Any]]:
        """
        Reads Kubernetes events looking for warning and error statuses.
        """
        result = run_kubectl_command(["get", "events", "-A", "-o", "json"])
        if not result["success"]:
            logger.warning(f"Failed to get events: {result['stderr']}")
            return [{"error": result["stderr"]}]

        try:
            data = json.loads(result["stdout"])
            findings = []
            
            target_reasons = {
                "FailedScheduling", "BackOff", "FailedMount", 
                "FailedPull", "ErrImagePull", "Unhealthy"
            }

            for item in data.get("items", []):
                reason = item.get("reason", "")
                type_ = item.get("type", "")
                
                # Check for critical warning types or target reasons
                if type_ == "Warning" or reason in target_reasons:
                    findings.append({
                        "namespace": item["metadata"].get("namespace", "default"),
                        "object": f"{item.get('involvedObject', {}).get('kind', '')}/{item.get('involvedObject', {}).get('name', '')}",
                        "reason": reason,
                        "message": item.get("message", ""),
                        "count": item.get("count", 1),
                        "last_timestamp": item.get("lastTimestamp", "")
                    })
            
            # Sort findings by timestamp or relevance, return top 20
            return findings[:20]
        except Exception as e:
            logger.exception("Failed to parse events json")
            return [{"error": f"Parse error: {str(e)}"}]


class DeploymentInspector:
    @staticmethod
    def inspect() -> List[Dict[str, Any]]:
        """
        Inspects deployments to check replicas and rollout health.
        """
        result = run_kubectl_command(["get", "deployments", "-A", "-o", "json"])
        if not result["success"]:
            logger.warning(f"Failed to get deployments: {result['stderr']}")
            return [{"error": result["stderr"]}]

        try:
            data = json.loads(result["stdout"])
            unhealthy_deployments = []

            for item in data.get("items", []):
                name = item["metadata"]["name"]
                namespace = item["metadata"]["namespace"]
                spec = item.get("spec", {})
                status = item.get("status", {})
                
                desired_replicas = spec.get("replicas", 1)
                updated_replicas = status.get("updatedReplicas", 0)
                ready_replicas = status.get("readyReplicas", 0)
                available_replicas = status.get("availableReplicas", 0)
                
                # Check for mismatch in replicas or rollout failures
                if (desired_replicas != ready_replicas) or (desired_replicas != available_replicas):
                    conditions = item.get("status", {}).get("conditions", [])
                    unhealthy_deployments.append({
                        "name": name,
                        "namespace": namespace,
                        "desired_replicas": desired_replicas,
                        "ready_replicas": ready_replicas,
                        "available_replicas": available_replicas,
                        "conditions": [
                            {"type": c.get("type", ""), "status": c.get("status", ""), "message": c.get("message", "")}
                            for c in conditions
                        ]
                    })
            return unhealthy_deployments
        except Exception as e:
            logger.exception("Failed to parse deployments json")
            return [{"error": f"Parse error: {str(e)}"}]


class NetworkInspector:
    @staticmethod
    def inspect() -> Dict[str, Any]:
        """
        Inspects services and endpoints to check selector matching.
        """
        services_res = run_kubectl_command(["get", "services", "-A", "-o", "json"])
        endpoints_res = run_kubectl_command(["get", "endpoints", "-A", "-o", "json"])

        if not services_res["success"] or not endpoints_res["success"]:
            return {
                "error": f"Failed to get network info. Svc error: {services_res['stderr']}. Endpoints error: {endpoints_res['stderr']}"
            }

        try:
            services_data = json.loads(services_res["stdout"])
            endpoints_data = json.loads(endpoints_res["stdout"])
            
            # Map endpoints by namespace/name
            endpoints_map = {}
            for ep in endpoints_data.get("items", []):
                ns = ep["metadata"]["namespace"]
                name = ep["metadata"]["name"]
                subsets = ep.get("subsets", [])
                endpoints_map[f"{ns}/{name}"] = subsets

            network_issues = []

            for svc in services_data.get("items", []):
                name = svc["metadata"]["name"]
                namespace = svc["metadata"]["namespace"]
                spec = svc.get("spec", {})
                selector = spec.get("selector", None)
                type_ = spec.get("type", "ClusterIP")

                # Kubernetes default service is fine to skip
                if name == "kubernetes" and namespace == "default":
                    continue

                # Check if it should match pods but has no endpoints
                if selector and type_ != "ExternalName":
                    ep_key = f"{namespace}/{name}"
                    subsets = endpoints_map.get(ep_key, [])
                    
                    has_endpoints = False
                    if subsets:
                        for subset in subsets:
                            if subset.get("addresses", []):
                                has_endpoints = True
                                break

                    if not has_endpoints:
                        network_issues.append({
                            "service_name": name,
                            "namespace": namespace,
                            "selector": selector,
                            "issue": "No active endpoints found. This indicates service selector mismatch or pods not running."
                        })

            return {
                "network_issues": network_issues,
                "services_count": len(services_data.get("items", []))
            }
        except Exception as e:
            logger.exception("Failed to parse network json")
            return {"error": f"Parse error: {str(e)}"}


def inspect_pods():
    """
    Expose basic pod inspection helper (kept for backwards compatibility if needed).
    """
    return PodInspector.inspect()
