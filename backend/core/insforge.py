import httpx
import json
from loguru import logger
from core import settings
from typing import Dict, Any, Optional

class InsForgeClient:
    def __init__(self):
        self.url = settings.INSFORGE_URL
        self.api_key = settings.INSFORGE_API_KEY

    async def execute_query(self, sql: str, params: list = None) -> Dict[str, Any]:
        """
        Executes a raw SQL query against the InsForge database using HTTP POST.
        """
        if not self.url or not self.api_key:
            logger.warning("InsForge credentials are not configured. Skipping database query.")
            return {"rows": [], "error": "Not configured"}

        endpoint = f"{self.url}/api/database/advance/rawsql"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": sql,
            "params": params or []
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"InsForge Query failed with status {response.status_code}: {response.text}")
                    return {"rows": [], "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.exception("Exception executing raw SQL query on InsForge")
            return {"rows": [], "error": str(e)}

    async def publish_progress(self, user_id: str, step: str, status: str) -> bool:
        """
        Publishes a realtime progress update message to investigation:<user_id> channel.
        """
        logger.info(f"Publishing progress to investigation:{user_id} - Step: {step}, Status: {status}")
        sql = "SELECT realtime.publish($1, $2, $3::jsonb);"
        payload = {
            "step": step,
            "status": status
        }
        params = [f"investigation:{user_id}", "progress", json.dumps(payload)]
        result = await self.execute_query(sql, params)
        return "error" not in result

    async def save_investigation(self, user_id: str, namespace: str, diagnosis: Dict[str, Any]) -> bool:
        """
        Persists completed SRE investigation details to the database history table.
        """
        logger.info(f"Saving investigation history for user: {user_id}")
        sql = (
            "INSERT INTO investigations (root_cause, namespace, confidence, status, user_id, explanation, fix, kubectl_command) "
            "VALUES ($1, $2, $3, $4, $5::uuid, $6, $7, $8);"
        )
        params = [
            diagnosis.get("root_cause", "Unknown"),
            namespace,
            diagnosis.get("confidence", 0),
            "success",
            user_id,
            diagnosis.get("explanation", ""),
            diagnosis.get("fix", ""),
            diagnosis.get("kubectl_command", "")
        ]
        result = await self.execute_query(sql, params)
        return "error" not in result

insforge_client = InsForgeClient()
