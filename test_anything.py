from services.anythingllm_client import AnythingLLMClient

client = AnythingLLMClient()

response = client.ask(
    "Créer un VLAN 100 server nommé RH"
)

print(response)