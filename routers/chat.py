from fastapi import APIRouter, Depends
from pydantic import BaseModel
from services.rag_service import get_personalized_challenge
from dependencies import get_current_user

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

@router.post("")
async def chat(req: ChatRequest, user = Depends(get_current_user)):
    """
    Reçoit un message de l'utilisateur,
    appelle le système RAG pour récupérer un défi personnalisé,
    retourne la réponse du chatbot + le défi.
    """
    result = await get_personalized_challenge(
        user_message=req.message,
        user_profile=user,
        history=req.history
    )
    return {
        "reply": result["reply"],
        "challenge": result.get("challenge")
    }