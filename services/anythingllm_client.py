import os
import requests
from dotenv import load_dotenv


load_dotenv()


class AnythingLLMClient:

    def __init__(self):
        self.base_url = os.getenv("ANYTHINGLLM_URL")
        self.workspace = os.getenv("ANYTHINGLLM_WORKSPACE")
        self.api_key = os.getenv("ANYTHINGLLM_API_KEY")

        if not self.base_url:
            raise ValueError("ANYTHINGLLM_URL n'est pas configuré")

        if not self.workspace:
            raise ValueError("ANYTHINGLLM_WORKSPACE n'est pas configuré")

        if not self.api_key:
            raise ValueError("ANYTHINGLLM_API_KEY n'est pas configuré")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def ask(self, prompt: str):

        url = (
            f"{self.base_url}"
            f"/api/v1/workspace/{self.workspace}/chat"
        )
        payload = {
            "message": prompt,
            "mode": "chat",
        }

        response = requests.post(
            url,
            headers=self.headers,
            json=payload,
            timeout=120,
        )

        response.raise_for_status()

        return response.json()

    