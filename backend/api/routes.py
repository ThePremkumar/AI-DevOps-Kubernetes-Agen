from fastapi import APIRouter
from models import DiagnosisResponse, InvestigationResponse, InvestigationRequest, ContextSelectRequest, ContextsResponse
from services import run_troubleshooting_flow, run_investigation
from kubernetes import get_available_contexts, switch_context

router = APIRouter()

@router.post("/investigate", response_model=DiagnosisResponse)
async def investigate_cluster(req: InvestigationRequest):
    """
    Endpoint to trigger an on-demand SRE cluster investigation and AI diagnosis.
    """
    result = await run_troubleshooting_flow(req.user_id, req.namespace)
    return DiagnosisResponse(status="success", diagnosis=result)

@router.get("/kubernetes/contexts", response_model=ContextsResponse)
def get_contexts():
    """
    Retrieves list of available Kubernetes contexts from kubeconfig.
    """
    result = get_available_contexts()
    return ContextsResponse(
        contexts=result["contexts"],
        current_context=result["current_context"]
    )

@router.post("/kubernetes/contexts/select")
def select_context(req: ContextSelectRequest):
    """
    Changes the active kubectl context.
    """
    result = switch_context(req.context)
    return result


