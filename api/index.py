import sys
import os
import importlib.util

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
backend_dir = os.path.join(root_dir, 'backend')

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Production must provide stable secrets and persistent database configuration.
# Do not silently generate per-instance values on Vercel: that can invalidate
# cryptographic state between serverless instances and hide deployment errors.
if os.environ.get("VERCEL"):
    if not os.environ.get("SECRET_KEY", "").strip():
        raise RuntimeError("SECRET_KEY must be configured in Vercel environment variables")
    if not os.environ.get("DATABASE_URL", "").strip():
        raise RuntimeError("DATABASE_URL must point to a persistent PostgreSQL database in Vercel")

app_py_path = os.path.join(backend_dir, 'app.py')
spec = importlib.util.spec_from_file_location("main_flask_app", app_py_path)
flask_module = importlib.util.module_from_spec(spec)
sys.modules["main_flask_app"] = flask_module
spec.loader.exec_module(flask_module)

app = flask_module.app
