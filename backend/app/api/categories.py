from fastapi import APIRouter
from app.services.category import get_all_categories

router = APIRouter(prefix="/api", tags=["categories"])


@router.get("/categories")
def list_categories():
    return get_all_categories()
