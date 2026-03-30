from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/signals")
def list_signals() -> dict[str, list[dict[str, object]]]:
    return {
        "items": [
            {"layer": "otc", "status": "pending"},
            {"layer": "wastewater", "status": "pending"},
            {"layer": "search", "status": "pending"},
        ]
    }
