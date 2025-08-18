# api/routes.py
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from ..schemas import ProblemInput
from ..controller.solve_loop import run_pipeline
from ..research.evaluation import ResearchEvaluationRunner
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


class ResearchEvalRequest(BaseModel):
    """Request model for research evaluation."""
    seeds: Optional[List[int]] = [42, 123, 456]
    max_workers: Optional[int] = 4
    output_dir: Optional[str] = "research_results"


class ResearchEvalResponse(BaseModel):
    """Response model for research evaluation."""
    message: str
    evaluation_id: str
    estimated_duration_minutes: float
    total_runs: int


@router.post("/research/evaluate", response_model=ResearchEvalResponse)
async def start_research_evaluation(request: ResearchEvalRequest, background_tasks: BackgroundTasks):
    """
    Start a 225-iteration research evaluation in the background.
    
    Returns immediately with evaluation ID and estimates.
    The actual evaluation runs in the background.
    """
    log.info(f"=== Research Evaluation Request Received ===")
    log.info(f"Request: {request.model_dump_json(indent=2)}")
    
    # Calculate estimates
    total_runs = 25 * len(request.seeds) * 3  # 25 tasks × seeds × 3 replans
    estimated_duration = total_runs * 60 / request.max_workers / 60  # Assume 60 seconds per run
    
    # Generate evaluation ID
    from datetime import datetime
    evaluation_id = f"research_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Start evaluation in background
    def run_evaluation():
        try:
            output_dir = Path(request.output_dir) / evaluation_id
            runner = ResearchEvaluationRunner(output_dir, max_workers=request.max_workers)
            analysis = runner.run_full_evaluation(seeds=request.seeds)
            log.info(f"✅ Research evaluation {evaluation_id} completed successfully")
            log.info(f"Final success rate: {analysis['evaluation_summary']['success_rate_percent']:.1f}%")
        except Exception as e:
            log.error(f"❌ Research evaluation {evaluation_id} failed: {e}")
    
    background_tasks.add_task(run_evaluation)
    
    response = ResearchEvalResponse(
        message=f"Research evaluation started with ID: {evaluation_id}",
        evaluation_id=evaluation_id,
        estimated_duration_minutes=estimated_duration,
        total_runs=total_runs
    )
    
    log.info(f"🚀 Research evaluation {evaluation_id} started in background")
    log.info(f"Response: {response.model_dump_json(indent=2)}")
    
    return response


@router.get("/research/status/{evaluation_id}")
async def get_research_status(evaluation_id: str):
    """
    Get the status of a research evaluation.
    
    Checks for result files to determine completion status.
    """
    log.info(f"Status check for evaluation: {evaluation_id}")
    
    # Look for result files - check multiple possible base directories
    possible_dirs = [
        Path("research_results") / evaluation_id,
        Path("test_research_results") / evaluation_id  # For testing
    ]
    
    base_dir = None
    for dir_path in possible_dirs:
        if dir_path.exists():
            base_dir = dir_path
            break
    
    if base_dir is None:
        base_dir = Path("research_results") / evaluation_id  # Default for error message
    
    if not base_dir.exists():
        return {
            "evaluation_id": evaluation_id,
            "status": "not_found",
            "message": "Evaluation not found"
        }
    
    # Check for completion files
    result_files = list(base_dir.glob("research_results_*.json"))
    analysis_files = list(base_dir.glob("research_analysis_*.json"))
    
    if result_files and analysis_files:
        # Evaluation completed
        try:
            # Load the most recent analysis
            latest_analysis = max(analysis_files, key=lambda p: p.stat().st_mtime)
            with open(latest_analysis, 'r') as f:
                import json
                analysis = json.load(f)
            
            return {
                "evaluation_id": evaluation_id,
                "status": "completed",
                "message": "Evaluation completed successfully",
                "summary": analysis["evaluation_summary"],
                "results_files": {
                    "detailed_results": str(result_files[-1]),
                    "analysis": str(analysis_files[-1])
                }
            }
        except Exception as e:
            return {
                "evaluation_id": evaluation_id,
                "status": "completed_with_errors",
                "message": f"Evaluation completed but failed to parse results: {e}"
            }
    else:
        # Still running
        return {
            "evaluation_id": evaluation_id,
            "status": "running",
            "message": "Evaluation is still in progress",
            "output_directory": str(base_dir)
        }