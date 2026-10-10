import uuid
from temporalio.client import Client
from workflows.aiops_workflow import AIOpsWorkflow


async def approve_workflow(workflow_id: str, decision: str):

    client = await Client.connect("localhost:7233")

    handle = client.get_workflow_handle(workflow_id)

    await handle.signal(
        AIOpsWorkflow.approve,
        decision
    )

    
async def start_workflow(prompt: str):

    client = await Client.connect(
        "localhost:7233"
    )

    workflow_id = f"aiops-{uuid.uuid4()}"

    handle = await client.start_workflow(
        AIOpsWorkflow.run,
        prompt,
        id=workflow_id,
        task_queue="aiops-task-queue",
    )

    return handle.id