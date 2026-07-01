import json
from typing import Dict, Any

class PromptBuilder:
    @staticmethod
    def get_system_prompt() -> str:
        return (
            "You are a Senior Kubernetes Site Reliability Engineer (SRE). "
            "Your job is to diagnose cluster failures based on the provided investigation evidence. "
            "Correlate the evidence across pods, logs, events, deployments, and network configurations to determine "
            "the precise root cause. "
            "You MUST reply with a valid JSON object ONLY. Do not include any markdown styling, "
            "code blocks (e.g. ```json), or explanatory text outside of the JSON. The JSON structure must match:\n"
            "{\n"
            '  "root_cause": "Short, clear description of the root cause",\n'
            '  "explanation": "Detailed correlation of evidence explaining why the failure happened",\n'
            '  "fix": "Actionable, step-by-step fix recommendation",\n'
            '  "kubectl_command": "The exact kubectl command(s) to edit/fix/debug the resource",\n'
            '  "confidence": 95\n'
            "}\n"
            "Confidence must be an integer between 0 and 100."
        )

    @staticmethod
    def build_user_prompt(evidence: Dict[str, Any]) -> str:
        """
        Formats Kubernetes troubleshooting evidence into a structured prompt.
        """
        pods_str = json.dumps(evidence.get("pods", {}), indent=2)
        logs_str = json.dumps(evidence.get("logs", {}), indent=2)
        events_str = json.dumps(evidence.get("events", []), indent=2)
        deployments_str = json.dumps(evidence.get("deployments", []), indent=2)
        network_str = json.dumps(evidence.get("network", {}), indent=2)

        return (
            f"Here is the collected Kubernetes troubleshooting evidence:\n\n"
            f"### Pod Status:\n{pods_str}\n\n"
            f"### Collected Logs:\n{logs_str}\n\n"
            f"### Cluster Events:\n{events_str}\n\n"
            f"### Deployments State:\n{deployments_str}\n\n"
            f"### Network & Services:\n{network_str}\n\n"
            f"Identify the root cause, explain it, suggest the exact fix, provide the kubectl command, and rate your confidence."
        )
