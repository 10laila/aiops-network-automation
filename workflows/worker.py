import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from workflows.aiops_workflow import AIOpsWorkflow

from workflows.activities import (
    ask_anythingllm,
    ask_gemini,
    validate_ai_response,
    generate_ansible_playbook,
    validate_playbook,
    execute_ansible_playbook,
    verify_network_configuration,
    format_ansible_result,
    push_to_gitea,
)


async def main():

    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="aiops-task-queue",
        workflows=[AIOpsWorkflow],
        activities=[ask_anythingllm, ask_gemini, validate_ai_response, generate_ansible_playbook, validate_playbook, execute_ansible_playbook, verify_network_configuration, format_ansible_result, push_to_gitea],
    )

    print("Worker démarré...")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())