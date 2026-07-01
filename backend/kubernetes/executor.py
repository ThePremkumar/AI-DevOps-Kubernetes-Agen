import os
import subprocess
from loguru import logger
from typing import Dict, Any, List

def prepare_kubeconfig() -> str:
    """
    Reads the mounted kubeconfig, rewrites localhost/127.0.0.1 references to host.docker.internal
    to allow container-to-host Kubernetes API communication, and returns the path to the temporary file.
    """
    original_path = "/root/.kube/config"
    target_path = "/app/kubeconfig_local"

    if not os.path.exists(original_path):
        logger.warning(f"Kubeconfig at {original_path} not found.")
        return ""

    try:
        with open(original_path, "r") as f:
            content = f.read()

        # Rewrite localhost & 127.0.0.1 to host.docker.internal
        rewritten = content.replace("https://127.0.0.1:", "https://host.docker.internal:")
        rewritten = rewritten.replace("https://localhost:", "https://host.docker.internal:")

        with open(target_path, "w") as f:
            f.write(rewritten)

        return target_path
    except Exception as e:
        logger.error(f"Failed to prepare local kubeconfig: {e}")
        return original_path

def run_kubectl_command(args: List[str], timeout: int = 15) -> Dict[str, Any]:
    """
    Safely executes a kubectl command using subprocess with the rewritten kubeconfig context.
    Returns a dictionary containing exit_code, stdout, stderr, and success status.
    """
    kubeconfig_path = prepare_kubeconfig()
    command = ["kubectl"] + args + ["--insecure-skip-tls-verify=true"]
    logger.info(f"Executing command: {' '.join(command)}")
    
    # Prepare custom env containing rewritten KUBECONFIG path
    env = os.environ.copy()
    if kubeconfig_path:
        env["KUBECONFIG"] = kubeconfig_path

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env
        )
        
        success = result.returncode == 0
        return {
            "success": success,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out: {' '.join(command)}")
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Error: Command timed out after {timeout} seconds"
        }
    except Exception as e:
        logger.exception(f"Unexpected error executing command: {' '.join(command)}")
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Unexpected error: {str(e)}"
        }
