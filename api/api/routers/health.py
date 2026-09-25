from fastapi import APIRouter
from api.config.settings import settings

router = APIRouter(tags=['health'])

@router.get('/health')
async def health():
    return {
        'status': 'ok',
        'demo_mode': settings.is_demo,
        'model_planner': settings.model_planner,
        'model_extract': settings.model_extract,
        'model_fast': settings.model_fast,
    }
