import os
import requests
from dotenv import load_dotenv

load_dotenv()

class GeminiClient:

    def __init__(self):
        self.base_url = os.getenv("GEMINI_GATEWAY_URL")

        if not self.base_url:
            raise ValueError(
                "GEMINI_GATEWAY_URL n'est pas configuré"
            )

    def ask(self, prompt: str):

        url = f"{self.base_url}/generate"

        response = requests.post(
            url,
            json={
                "prompt": prompt
            },
            timeout=120
        )
        response.raise_for_status()

        return response.json()