from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# ---------------------------------------------------------
# UI PATHS
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
UI_DIR = os.path.join(BASE_DIR, "ui")
ASSETS_DIR = os.path.join(UI_DIR, "assets")

# ---------------------------------------------------------
# STATIC ASSETS
# ---------------------------------------------------------
if os.path.isdir(ASSETS_DIR):
    app.mount("/ui/assets", StaticFiles(directory=ASSETS_DIR), name="ui-assets")

# ---------------------------------------------------------
# INDEX ROUTE
# ---------------------------------------------------------
@app.get("/ui")
def serve_ui():
    index_file = os.path.join(UI_DIR, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    return {"error": "UI not found. Build the cockpit UI and copy dist/ into ui/"}

# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "organ": "cockpit-backend"}
