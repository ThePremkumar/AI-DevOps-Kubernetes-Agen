from loguru import logger
from kubernetes.inspector import PodInspector, LogsCollector, EventsAnalyzer, DeploymentInspector, NetworkInspector
from ai import analyze_root_cause
from core.insforge import insforge_client

def run_investigation():
    """
    Orchestrates the evidence-gathering flow across pods, logs, events, deployments, and network.
    """
    logger.info("Starting Kubernetes cluster investigation")
    
    # 1. Check pods
    pods_data = PodInspector.inspect()
    
    # 2. Collect logs for problematic pods
    problematic_pods = pods_data.get("problematic_pods", [])
    logs_data = LogsCollector.collect(problematic_pods)
    
    # 3. Analyze events
    events_data = EventsAnalyzer.analyze()
    
    # 4. Inspect deployments
    deployments_data = DeploymentInspector.inspect()
    
    # 5. Check networking
    network_data = NetworkInspector.inspect()
    
    return {
        "pods": pods_data,
        "logs": logs_data,
        "events": events_data,
        "deployments": deployments_data,
        "network": network_data
    }

async def run_troubleshooting_flow(user_id: str, namespace: str = "default"):
    """
    Coordinates SRE troubleshooting flow: gathers evidence, runs AI analysis, publishes live progress,
    and saves investigation results to InsForge.
    """
    logger.info(f"Running SRE AI troubleshooting flow for user {user_id} in namespace {namespace}")
    
    # 1. Check Pods
    await insforge_client.publish_progress(user_id, "Checking Pods", "in-progress")
    pods_data = PodInspector.inspect()
    await insforge_client.publish_progress(user_id, "Checking Pods", "completed")
    
    # 2. Read Logs
    await insforge_client.publish_progress(user_id, "Reading Logs", "in-progress")
    problematic_pods = pods_data.get("problematic_pods", [])
    logs_data = LogsCollector.collect(problematic_pods)
    await insforge_client.publish_progress(user_id, "Reading Logs", "completed")
    
    # 3. Analyze Events
    await insforge_client.publish_progress(user_id, "Analyzing Events", "in-progress")
    events_data = EventsAnalyzer.analyze()
    await insforge_client.publish_progress(user_id, "Analyzing Events", "completed")
    
    # 4. Inspect Deployments
    await insforge_client.publish_progress(user_id, "Inspecting Deployments", "in-progress")
    deployments_data = DeploymentInspector.inspect()
    await insforge_client.publish_progress(user_id, "Inspecting Deployments", "completed")
    
    # 5. Check Networking
    await insforge_client.publish_progress(user_id, "Checking Networking", "in-progress")
    network_data = NetworkInspector.inspect()
    await insforge_client.publish_progress(user_id, "Checking Networking", "completed")
    
    # Pack evidence
    evidence = {
        "pods": pods_data,
        "logs": logs_data,
        "events": events_data,
        "deployments": deployments_data,
        "network": network_data
    }
    
    # 6. AI Reasoning
    await insforge_client.publish_progress(user_id, "AI Reasoning", "in-progress")
    diagnosis = await analyze_root_cause(evidence)
    await insforge_client.publish_progress(user_id, "AI Reasoning", "completed")
    
    # 7. Save to history and complete
    await insforge_client.save_investigation(user_id, namespace, diagnosis)
    await insforge_client.publish_progress(user_id, "Root Cause Found", "completed")
    
    return diagnosis
