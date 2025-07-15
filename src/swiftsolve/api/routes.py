# api/routes.py
from fastapi import APIRouter
from schemas.plan import ProblemInput
from controller.solve_loop import run_pipeline

router = APIRouter()

@router.post("/solve")
async def solve(input_data: ProblemInput):
    return run_pipeline(input_data)