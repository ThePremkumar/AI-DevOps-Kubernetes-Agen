import httpx
from loguru import logger
from core import settings
from typing import Dict, Any, Optional

class LLMClient:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL or "anthropic/claude-3-sonnet"
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    async def get_completion(self, system_prompt: str, user_prompt: str, timeout: float = 30.0) -> Optional[str]:
        """
        Sends a request to OpenRouter API to fetch LLM completion.
        Returns the completed text response or None if it fails.
        """
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY is not configured. Skipping LLM request.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "AI Kubernetes Agent",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
        }

        logger.info(f"Sending completion request to OpenRouter using model: {self.model}")

        # Retry logic: Try up to 3 times
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(self.url, headers=headers, json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        choices = data.get("choices", [])
                        if choices:
                            content = choices[0].get("message", {}).get("content", "")
                            return content.strip()
                        else:
                            logger.error(f"OpenRouter response did not contain choices: {data}")
                            return None
                    else:
                        logger.error(f"OpenRouter returned status code {response.status_code}: {response.text} (Attempt {attempt}/{max_retries})")
            except httpx.RequestError as e:
                logger.error(f"HTTP connection error to OpenRouter: {str(e)} (Attempt {attempt}/{max_retries})")
            except Exception as e:
                logger.exception(f"Unexpected error in LLM completion (Attempt {attempt}/{max_retries})")

        return None
