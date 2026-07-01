from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class HealthResponse(BaseModel):
    status: str
    service: str

class DiagnosisDetails(BaseModel):
    root_cause: str
    explanation: str
    fix: str
    kubectl_command: str
    confidence: int

class DiagnosisResponse(BaseModel):
    status: str
    diagnosis: DiagnosisDetails


class InvestigationPayload(BaseModel):
    pods: Dict[str, Any]
    logs: Dict[str, str]
    events: Any
    deployments: Any
    network: Dict[str, Any]

class InvestigationResponse(BaseModel):
    status: str
    investigation: InvestigationPayload

class InvestigationRequest(BaseModel):
    user_id: str
    namespace: Optional[str] = "default"

class ContextSelectRequest(BaseModel):
    context: str

class ContextsResponse(BaseModel):
    contexts: List[str]
    current_context: Optional[str]


