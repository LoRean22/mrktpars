from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class SearchCreate(BaseModel):
    user_id: int
    search_url: str
    interval: int

@router.post("/searches")
def create_search(search: SearchCreate):
    return {"status": "ok", "search": search}
