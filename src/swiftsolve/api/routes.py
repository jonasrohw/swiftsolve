# api/routes.py
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
from ..schemas import ProblemInput
from ..controller.solve_loop import run_pipeline
from ..research.evaluation import ResearchEvaluationRunner
from ..research.data_export import ResearchDataExporter
from ..baseline.evaluation import BaselineEvaluationRunner
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
    resume_evaluation_id: Optional[str] = None  # For resuming interrupted evaluations


class ResearchEvalResponse(BaseModel):
    """Response model for research evaluation."""
    message: str
    evaluation_id: str
    estimated_duration_minutes: float
    total_runs: int


class MiniResearchEvalRequest(BaseModel):
    """Request model for mini research evaluation."""
    seeds: Optional[List[int]] = [42, 123, 456]
    max_workers: Optional[int] = 2
    output_dir: Optional[str] = "mini_research_results"


class MiniResearchEvalResponse(BaseModel):
    """Response model for mini research evaluation."""
    message: str
    evaluation_id: str
    estimated_duration_minutes: float
    total_runs: int


@router.post("/research/evaluate", response_model=ResearchEvalResponse)
async def start_research_evaluation(request: ResearchEvalRequest, background_tasks: BackgroundTasks):
    """
    Start a comprehensive 225-iteration research evaluation in the background.
    
    Returns immediately with evaluation ID and estimates.
    The actual evaluation runs in the background.
    """
    log.info(f"=== Research Evaluation Request Received ===")
    log.info(f"Request: {request.model_dump_json(indent=2)}")
    
    # Calculate estimates
    total_runs = 25 * len(request.seeds) * 3  # 25 tasks × seeds × 3 replans
    estimated_duration = total_runs * 60 / request.max_workers / 60  # Assume 60 seconds per run
    
    # Generate or use existing evaluation ID
    from datetime import datetime
    if request.resume_evaluation_id:
        evaluation_id = request.resume_evaluation_id
        log.info(f"🔄 RESUMING evaluation with ID: {evaluation_id}")
    else:
        evaluation_id = f"research_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        log.info(f"🚀 Starting NEW evaluation with ID: {evaluation_id}")
    
    # Start evaluation in background
    def run_evaluation():
        try:
            output_dir = Path(request.output_dir) / evaluation_id
            runner = ResearchEvaluationRunner(output_dir, max_workers=request.max_workers)
            analysis = runner.run_full_evaluation(seeds=request.seeds, evaluation_id=evaluation_id)
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


@router.post("/mini-research/evaluate", response_model=MiniResearchEvalResponse)
async def start_mini_research_evaluation(request: MiniResearchEvalRequest, background_tasks: BackgroundTasks):
    """
    Start a mini research evaluation in the background (18 iterations instead of 225).
    
    Mini evaluation: 2 tasks × 3 seeds × 3 replans = 18 iterations total.
    Perfect for testing your setup before running the full benchmark.
    
    Returns immediately with evaluation ID and estimates.
    The actual evaluation runs in the background.
    """
    log.info(f"=== Mini Research Evaluation Request Received ===")
    log.info(f"Request: {request.model_dump_json(indent=2)}")
    
    # Calculate estimates for mini run
    total_runs = 2 * len(request.seeds) * 3  # 2 tasks × seeds × 3 replans
    estimated_duration = total_runs * 60 / request.max_workers / 60  # Assume 60 seconds per run
    
    # Generate evaluation ID
    from datetime import datetime
    evaluation_id = f"mini_research_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Start mini evaluation in background
    def run_mini_evaluation():
        try:
            output_dir = Path(request.output_dir) / evaluation_id
            runner = ResearchEvaluationRunner(output_dir, max_workers=request.max_workers)
            analysis = runner.run_full_evaluation(seeds=request.seeds, mini_run=True)
            log.info(f"✅ Mini research evaluation {evaluation_id} completed successfully")
            log.info(f"Final success rate: {analysis['evaluation_summary']['success_rate_percent']:.1f}%")
        except Exception as e:
            log.error(f"❌ Mini research evaluation {evaluation_id} failed: {e}")
    
    background_tasks.add_task(run_mini_evaluation)
    
    response = MiniResearchEvalResponse(
        message=f"Mini research evaluation started with ID: {evaluation_id}",
        evaluation_id=evaluation_id,
        estimated_duration_minutes=estimated_duration,
        total_runs=total_runs
    )
    
    log.info(f"🚀 Mini research evaluation {evaluation_id} started in background")
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
        Path("test_research_results") / evaluation_id,  # For testing
        Path("test_research_results_fixed") / evaluation_id  # For latest testing
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


class ExportResponse(BaseModel):
    """Response model for data export operations."""
    message: str
    evaluation_id: str
    export_summary: Dict[str, Any]
    files_created: int


@router.post("/research/export/{evaluation_id}", response_model=ExportResponse)
async def export_research_data(evaluation_id: str, output_dir: Optional[str] = None):
    """
    Export research data for figures and analysis.
    
    Exports:
    - Runtime curves (Figure 6.2)
    - TLE/MLE rates (Figure 6.3) 
    - Iteration analysis (Figure 6.4)
    """
    log.info(f"=== Export Research Data Request for {evaluation_id} ===")
    
    # Find result files for this evaluation
    search_dirs = ["research_results", "mini_research_results", "mini_test_api", "mini_3seeds_test"]
    results_file = None
    
    for search_dir in search_dirs:
        search_path = Path(search_dir)
        if search_path.exists():
            for eval_dir in search_path.glob(f"*{evaluation_id}*"):
                for file in eval_dir.glob("research_results_*.json"):
                    results_file = file
                    break
                if results_file:
                    break
    
    if not results_file:
        return ExportResponse(
            message=f"No results found for evaluation {evaluation_id}",
            evaluation_id=evaluation_id,
            export_summary={},
            files_created=0
        )
    
    # Set output directory
    if not output_dir:
        output_dir = f"exports/{evaluation_id}"
    
    try:
        # Export all research data
        exporter = ResearchDataExporter(results_file)
        exports = exporter.export_all_research_data(Path(output_dir))
        
        total_files = sum(len(files) for files in exports.values())
        
        return ExportResponse(
            message=f"Successfully exported research data for {evaluation_id}",
            evaluation_id=evaluation_id,
            export_summary={k: [str(p) for p in v] for k, v in exports.items()},
            files_created=total_files
        )
        
    except Exception as e:
        log.error(f"Export failed for {evaluation_id}: {e}")
        return ExportResponse(
            message=f"Export failed: {str(e)}",
            evaluation_id=evaluation_id,
            export_summary={},
            files_created=0
        )


@router.get("/research/curves/{evaluation_id}")
async def get_runtime_curves(evaluation_id: str):
    """
    Get runtime curve data for plotting (Figure 6.2).
    
    Returns JSON data suitable for plotting libraries.
    """
    log.info(f"=== Runtime Curves Request for {evaluation_id} ===")
    
    # Find and load results
    search_dirs = ["research_results", "mini_research_results", "mini_test_api", "mini_3seeds_test"]
    results_file = None
    
    for search_dir in search_dirs:
        search_path = Path(search_dir)
        if search_path.exists():
            for eval_dir in search_path.glob(f"*{evaluation_id}*"):
                for file in eval_dir.glob("research_results_*.json"):
                    results_file = file
                    break
                if results_file:
                    break
    
    if not results_file:
        return {"error": f"No results found for evaluation {evaluation_id}"}
    
    try:
        exporter = ResearchDataExporter(results_file)
        
        # Extract runtime curve data
        runtime_data = []
        for result in exporter.results_data.get('results', []):
            if result.get('status') == 'success' and result.get('profile_report'):
                profile = result['profile_report']
                if 'input_sizes' in profile and 'runtime_ms' in profile:
                    runtime_data.append({
                        'task_id': result['task_id'],
                        'seed': result['seed'],
                        'replan_id': result['replan_id'],
                        'input_sizes': profile['input_sizes'],
                        'runtime_ms': profile['runtime_ms'],
                        'peak_memory_mb': profile.get('peak_memory_mb', [])
                    })
        
        return {
            "evaluation_id": evaluation_id,
            "curve_count": len(runtime_data),
            "curves": runtime_data
        }
        
    except Exception as e:
        log.error(f"Failed to get runtime curves for {evaluation_id}: {e}")
        return {"error": f"Failed to load runtime curves: {str(e)}"}


# ================================================================================
# BASELINE EVALUATION ENDPOINTS
# ================================================================================

class BaselineEvalRequest(BaseModel):
    """Request model for baseline evaluation."""
    seeds: Optional[List[int]] = [42, 123, 456]
    max_workers: Optional[int] = 4
    output_dir: Optional[str] = "baseline_test_api"


class BaselineEvalResponse(BaseModel):
    """Response model for baseline evaluation."""
    message: str
    evaluation_id: str
    estimated_duration_minutes: float
    total_runs: int


class MiniBaselineEvalRequest(BaseModel):
    """Request model for mini baseline evaluation."""
    seeds: Optional[List[int]] = [42, 123, 456]
    max_workers: Optional[int] = 2
    output_dir: Optional[str] = "mini_baseline_results"


class MiniBaselineEvalResponse(BaseModel):
    """Response model for mini baseline evaluation."""
    message: str
    evaluation_id: str
    estimated_duration_minutes: float
    total_runs: int


@router.post("/baseline/evaluate", response_model=BaselineEvalResponse)
async def start_baseline_evaluation(request: BaselineEvalRequest, background_tasks: BackgroundTasks):
    """
    Start a comprehensive 75-iteration baseline evaluation using GPT-4 directly.
    
    This serves as a robust baseline for comparing against SwiftSolve.
    Uses GPT-4 directly (single attempt per problem) instead of the planner+coder+analyst pipeline.
    
    Returns immediately with evaluation ID and estimates.
    The actual evaluation runs in the background.
    """
    log.info(f"=== Baseline Evaluation Request Received ===")
    log.info(f"Request: {request.model_dump_json(indent=2)}")
    
    # Calculate estimates
    total_runs = 25 * len(request.seeds)  # 25 tasks × seeds (no replanning)
    estimated_duration = total_runs * 30 / request.max_workers / 60  # Assume 30 seconds per run (single attempt)
    
    # Generate evaluation ID
    from datetime import datetime
    evaluation_id = f"baseline_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log.info(f"🚀 Starting BASELINE evaluation with ID: {evaluation_id}")
    
    # Start evaluation in background
    def run_baseline_evaluation():
        try:
            output_dir = Path(request.output_dir) / evaluation_id
            runner = BaselineEvaluationRunner(output_dir, max_workers=request.max_workers)
            analysis = runner.run_full_evaluation(seeds=request.seeds)
            log.info(f"✅ Baseline evaluation {evaluation_id} completed successfully")
            log.info(f"Final success rate: {analysis['evaluation_summary']['success_rate_percent']:.1f}%")
        except Exception as e:
            log.error(f"❌ Baseline evaluation {evaluation_id} failed: {e}")
    
    background_tasks.add_task(run_baseline_evaluation)
    
    response = BaselineEvalResponse(
        message=f"Baseline evaluation started with ID: {evaluation_id}",
        evaluation_id=evaluation_id,
        estimated_duration_minutes=estimated_duration,
        total_runs=total_runs
    )
    
    log.info(f"🚀 Baseline evaluation {evaluation_id} started in background")
    log.info(f"Response: {response.model_dump_json(indent=2)}")
    
    return response


@router.post("/mini-baseline/evaluate", response_model=MiniBaselineEvalResponse)
async def start_mini_baseline_evaluation(request: MiniBaselineEvalRequest, background_tasks: BackgroundTasks):
    """
    Start a mini baseline evaluation using GPT-4 directly (6 iterations instead of 75).
    
    Mini evaluation: 2 tasks × 3 seeds = 6 iterations total (single attempt per problem).
    Perfect for testing the baseline setup before running the full benchmark.
    
    Returns immediately with evaluation ID and estimates.
    The actual evaluation runs in the background.
    """
    log.info(f"=== Mini Baseline Evaluation Request Received ===")
    log.info(f"Request: {request.model_dump_json(indent=2)}")
    
    # Calculate estimates for mini run
    total_runs = 2 * len(request.seeds)  # 2 tasks × seeds (no replanning)
    estimated_duration = total_runs * 30 / request.max_workers / 60  # Assume 30 seconds per run
    
    # Generate evaluation ID
    from datetime import datetime
    evaluation_id = f"mini_baseline_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Start mini evaluation in background
    def run_mini_baseline_evaluation():
        try:
            output_dir = Path(request.output_dir) / evaluation_id
            runner = BaselineEvaluationRunner(output_dir, max_workers=request.max_workers)
            analysis = runner.run_full_evaluation(seeds=request.seeds, mini_run=True)
            log.info(f"✅ Mini baseline evaluation {evaluation_id} completed successfully")
            log.info(f"Final success rate: {analysis['evaluation_summary']['success_rate_percent']:.1f}%")
        except Exception as e:
            log.error(f"❌ Mini baseline evaluation {evaluation_id} failed: {e}")
    
    background_tasks.add_task(run_mini_baseline_evaluation)
    
    response = MiniBaselineEvalResponse(
        message=f"Mini baseline evaluation started with ID: {evaluation_id}",
        evaluation_id=evaluation_id,
        estimated_duration_minutes=estimated_duration,
        total_runs=total_runs
    )
    
    log.info(f"🚀 Mini baseline evaluation {evaluation_id} started in background")
    log.info(f"Response: {response.model_dump_json(indent=2)}")
    
    return response


@router.get("/baseline/status/{evaluation_id}")
async def get_baseline_status(evaluation_id: str):
    """
    Get the status of a baseline evaluation.
    
    Checks for result files to determine completion status.
    """
    log.info(f"Status check for baseline evaluation: {evaluation_id}")
    
    # Look for result files - check multiple possible base directories
    possible_dirs = [
        Path("baseline_test_api") / evaluation_id,
        Path("mini_baseline_results") / evaluation_id,
        Path("baseline_results") / evaluation_id  # fallback
    ]
    
    base_dir = None
    for dir_path in possible_dirs:
        if dir_path.exists():
            base_dir = dir_path
            break
    
    if base_dir is None:
        base_dir = Path("baseline_test_api") / evaluation_id  # Default for error message
    
    if not base_dir.exists():
        return {
            "evaluation_id": evaluation_id,
            "status": "not_found",
            "message": "Baseline evaluation not found"
        }
    
    # Check for completion files
    result_files = list(base_dir.glob("baseline_results_*.json"))
    analysis_files = list(base_dir.glob("baseline_analysis_*.json"))
    
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
                "message": "Baseline evaluation completed successfully",
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
                "message": f"Baseline evaluation completed but failed to parse results: {e}"
            }
    else:
        # Still running
        return {
            "evaluation_id": evaluation_id,
            "status": "running",
            "message": "Baseline evaluation is still in progress",
            "output_directory": str(base_dir)
        }