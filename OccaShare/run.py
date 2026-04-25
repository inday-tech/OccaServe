"""Helper script to start the FastAPI application.

Launching this script installs the package path automatically so that
`app` can be imported without adjusting PYTHONPATH or changing directory.
"""

import os
import sys

# Ensure the package root is on sys.path so `import app` works no matter
# where the script is executed from.
root = os.path.dirname(os.path.abspath(__file__))
if root not in sys.path:
    sys.path.insert(0, root)

import uvicorn

if __name__ == "__main__":
    # Get port from environment variable for cloud deployment (e.g., Railway, Heroku)
    port = int(os.environ.get("PORT", 8000))
    
    # Disable reload in production (when PORT is set) for better performance and stability
    is_reload = True if not os.environ.get("PORT") else False
    
    print(f"Starting server on port {port} (reload={is_reload})")
    
    # full package path to the application object
    uvicorn.run("app.main:app", reload=is_reload, host="0.0.0.0", port=port)
