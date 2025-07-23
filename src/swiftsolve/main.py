import argparse
from fastapi import FastAPI
from .api.routes import router
from .controller.solve_loop import run_pipeline
from .schemas import ProblemInput
import json, pathlib

def make_app():
    app = FastAPI(title="SwiftSolve API")
    app.include_router(router)
    return app

# Create the app instance for uvicorn
app = make_app()

def _cli():
    p = argparse.ArgumentParser()
    p.add_argument("--task_json", required=True)
    args = p.parse_args()
    task = ProblemInput(**json.loads(pathlib.Path(args.task_json).read_text()))
    res = run_pipeline(task)
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    _cli()