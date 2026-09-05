from fastapi import APIRouter, HTTPException
from ai_assistant.assistant import WarehouseAssistant
from ai_assistant.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/assistant", tags=["assistant"])
assistant = WarehouseAssistant()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = assistant.ask(request.question, request.selected_event_id)
    except Exception as exc:  # narrow this once real backend error types are known
        raise HTTPException(status_code=502, detail=str(exc))
    return ChatResponse(answer=result["answer"], tools_used=result["tools_used"])