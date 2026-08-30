import sys
import os
import traceback

# Add current dir, parent dir (root), and backend dir to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
backend_dir = os.path.join(root_dir, "backend")

for p in [current_dir, root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from app.main import app
except Exception as e1:
    try:
        from backend.app.main import app
    except Exception as e2:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        app = FastAPI(title="Plexudo Fallback")

        @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
        async def fallback_error(path: str = ""):
            tb = traceback.format_exc()
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Plexudo Backend Serverless Startup Exception",
                    "exception_1": str(e1),
                    "exception_2": str(e2),
                    "traceback": tb,
                    "sys_path": sys.path,
                },
            )
