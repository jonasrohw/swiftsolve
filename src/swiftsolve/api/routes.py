# api/routes.py
from fastapi import APIRouter
from ..schemas import ProblemInput
from ..controller.solve_loop import run_pipeline
from ..utils.logger import get_logger

log = get_logger("API")

router = APIRouter()

@router.get("/healthz")
async def health_check():
    log.info("Health check request received")
    return {
        "status": "healthy",
        "service": "swiftsolve",
        "version": "1.0.0"
    }

@router.post("/solve")
async def solve(input_data: ProblemInput):
    log.info(f"=== API Request Received ===")
    log.info(f"Request data: {input_data.model_dump_json(indent=2)}")
    
    try:
        result = run_pipeline(input_data)
        log.info(f"Pipeline completed successfully")
        log.info(f"Result: {result}")
        return result
    except Exception as e:
        log.error(f"Pipeline failed with exception: {e}")
        log.error(f"Exception type: {type(e).__name__}")
        raise