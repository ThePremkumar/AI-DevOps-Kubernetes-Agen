from loguru import logger
from typing import List, Dict, Any, Optional
from .executor import run_kubectl_command

def get_available_contexts() -> Dict[str, Any]:
    """
    Retrieves all available Kubernetes contexts from kubeconfig and the active context.
    """
    contexts_res = run_kubectl_command(["config", "get-contexts", "-o", "name"])
    current_res = run_kubectl_command(["config", "current-context"])
    
    contexts = []
    if contexts_res["success"]:
        stdout = contexts_res["stdout"].strip()
        if stdout:
            contexts = stdout.splitlines()
    else:
        logger.warning(f"Failed to get contexts: {contexts_res['stderr']}")

    current_context = None
    if current_res["success"]:
        current_context = current_res["stdout"].strip()
    else:
        logger.warning(f"Failed to get current context: {current_res['stderr']}")

    return {
        "contexts": contexts,
        "current_context": current_context
    }

def switch_context(context_name: str) -> Dict[str, Any]:
    """
    Switches the active kubectl context to the specified one.
    """
    logger.info(f"Switching kubectl context to: {context_name}")
    result = run_kubectl_command(["config", "use-context", context_name])
    return {
        "success": result["success"],
        "message": result["stdout"] if result["success"] else result["stderr"]
    }
