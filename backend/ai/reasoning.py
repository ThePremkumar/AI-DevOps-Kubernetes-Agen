import json
from loguru import logger
from typing import Dict, Any
from .client import LLMClient
from .prompt import PromptBuilder

def run_local_heuristics(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback heuristic engine to diagnose common Kubernetes issues locally.
    """
    logger.info("Executing local heuristic analysis fallback")
    
    pods = evidence.get("pods", {})
    logs = evidence.get("logs", {})
    events = evidence.get("events", [])
    network = evidence.get("network", {})
    deployments = evidence.get("deployments", [])

    # 1. Check for Kubeconfig connection failures
    if pods.get("error") or network.get("error"):
        return {
            "root_cause": "Kubernetes Cluster Unreachable",
            "explanation": "The agent was unable to connect to the cluster. Kubectl commands are failing.",
            "fix": "Please check if your Kubernetes cluster is running and verify that your KUBECONFIG file is correctly configured and mounted.",
            "kubectl_command": "kubectl cluster-info",
            "confidence": 99
        }

    # 2. Check for Pod Status Errors
    problematic_pods = pods.get("problematic_pods", [])
    if problematic_pods:
        first_pod = problematic_pods[0]
        pod_name = first_pod.get("name", "")
        status = first_pod.get("status", "")
        namespace = first_pod.get("namespace", "default")
        
        # Check corresponding logs for common errors
        pod_logs = logs.get(f"{namespace}/{pod_name}", "")
        
        if "DATABASE_URL" in pod_logs or "database" in pod_logs.lower() or "conn" in pod_logs.lower():
            return {
                "root_cause": "Database Connection Refused",
                "explanation": f"Pod {pod_name} is failing due to database connection errors shown in logs.",
                "fix": "Verify that the database service is running and that the credentials/environment variables (like DATABASE_URL) are correctly configured.",
                "kubectl_command": f"kubectl logs {pod_name} -n {namespace}",
                "confidence": 90
            }
        
        if "CrashLoopBackOff" in status:
            return {
                "root_cause": "Application Crash on Startup (CrashLoopBackOff)",
                "explanation": f"The pod {pod_name} started successfully but exited immediately with a failure state.",
                "fix": "Inspect the container logs and events to debug startup exceptions or missing configuration parameters.",
                "kubectl_command": f"kubectl logs {pod_name} -n {namespace} --previous",
                "confidence": 85
            }
            
        if "ImagePullBackOff" in status or "ErrImagePull" in status:
            return {
                "root_cause": "Container Image Pull Failure",
                "explanation": f"Kubernetes is unable to pull the Docker image specified in the pod definition for {pod_name}.",
                "fix": "Verify the image name and tag are correct, check registry credentials, and ensure the image is publicly available or imagePullSecrets are configured.",
                "kubectl_command": f"kubectl describe pod {pod_name} -n {namespace}",
                "confidence": 95
            }

    # 3. Check for Network Selector mismatch
    network_issues = network.get("network_issues", [])
    if network_issues:
        first_issue = network_issues[0]
        svc_name = first_issue.get("service_name", "")
        ns = first_issue.get("namespace", "default")
        return {
            "root_cause": "Service Selector Mismatch",
            "explanation": f"The service {svc_name} in namespace {ns} has selectors that do not match any running pods. Endpoints list is empty.",
            "fix": "Update the service selector labels to align with the labels configured on the deployment's template spec.",
            "kubectl_command": f"kubectl edit svc {svc_name} -n {ns}",
            "confidence": 95
        }

    # 4. Check events
    for event in events:
        if isinstance(event, dict) and event.get("reason") == "FailedMount":
            return {
                "root_cause": "Volume Mount Failure",
                "explanation": f"Mount failure detected for object {event.get('object')}. Message: {event.get('message')}",
                "fix": "Ensure that the PersistentVolumeClaim (PVC) or ConfigMap exists and is bound/configured correctly in the namespace.",
                "kubectl_command": f"kubectl get pvc -n {event.get('namespace')}",
                "confidence": 90
            }

    # 5. Default healthy diagnosis
    return {
        "root_cause": "No Critical Failures Found",
        "explanation": "The heuristic analyzer did not detect any immediate, obvious pod status errors, network configuration problems, or failed rollouts.",
        "fix": "Continue monitoring the cluster or run specific performance checks if workloads are experiencing latency.",
        "kubectl_command": "kubectl get all -A",
        "confidence": 95
    }

async def analyze_root_cause(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coordinates building prompts, sending them to OpenRouter LLM, and parsing responses.
    Falls back to a local SRE heuristic analyzer if OpenRouter is unreachable.
    """
    system_prompt = PromptBuilder.get_system_prompt()
    user_prompt = PromptBuilder.build_user_prompt(evidence)
    
    client = LLMClient()
    response_text = await client.get_completion(system_prompt, user_prompt)
    
    if response_text:
        try:
            # Clean possible markdown wrapping if the LLM output is not completely clean
            cleaned_text = response_text
            if cleaned_text.startswith("```"):
                lines = cleaned_text.splitlines()
                # Remove first and last lines
                if len(lines) >= 3:
                    cleaned_text = "\n".join(lines[1:-1])
            
            parsed_json = json.loads(cleaned_text)
            logger.info("Successfully analyzed and parsed SRE diagnosis from OpenRouter")
            return parsed_json
        except Exception as e:
            logger.error(f"Failed to parse LLM json response: {str(e)}. Raw text: {response_text}")
    
    # Fall back to local heuristics
    return run_local_heuristics(evidence)
