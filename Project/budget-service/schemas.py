from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []
    currency: str = "vnd"
    rate: float = 1.0

class AIRequest(BaseModel):
    text: str
    currency: str = "vnd"
    rate: float = 1.0