from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import json

app = FastAPI(title="UW Medicine Hierarchy Explorer")

DATA_PATH = Path(__file__).parent.parent / "systems" / "uw-medicine" / "hierarchy.json"

@app.get("/api/hierarchy")
def get_hierarchy():
    with open(DATA_PATH) as f:
        return json.load(f)

@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8646)