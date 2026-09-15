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

# Keep the WSGI entrypoint importable even when Vercel environment variables are
# not configured yet. The application configuration remains responsible for
# using a secure SECRET_KEY when provided and can fall back to a per-instance
# development secret when none is available. This prevents the entire API
# function from failing before Flask can return a JSON error response.

app_py_path = os.path.join(backend_dir, 'app.py')
spec = importlib.util.spec_from_file_location("main_flask_app", app_py_path)
flask_module = importlib.util.module_from_spec(spec)
sys.modules["main_flask_app"] = flask_module
spec.loader.exec_module(flask_module)

app = flask_module.app
