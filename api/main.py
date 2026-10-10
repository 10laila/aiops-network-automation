from fastapi import FastAPI
from pydantic import BaseModel
from workflows.client import approve_workflow, start_workflow

app = FastAPI(
    title="Temporal API",
    version="1.0.0"
)

class RequestModel(BaseModel):
    prompt: str

@app.get("/")
async def root():
    return {"message": "AIOps API is running"}

@app.post("/request")
async def request_aiops(request: RequestModel):
    result = await start_workflow(request.prompt)

    return {
        "result": result
    }

class ApprovalRequest(BaseModel):
    workflow_id: str
    decision: str

@app.post("/approve")
async def approve_workflow_api(request: ApprovalRequest):

    if request.decision not in ["approved", "rejected"]:
        return {
            "success": False,
            "message": "La décision doit être approved ou rejected."
        }

    await approve_workflow(
        request.workflow_id,
        request.decision
    )

    return {
        "success": True,
        "workflow_id": request.workflow_id,
        "decision": request.decision,
        "message": "Décision envoyée à Temporal."
    }