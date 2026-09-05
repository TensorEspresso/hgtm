"""HS2 hierarchy explorer — FastAPI backend.

Endpoints:
  GET /                  -> index.html
  GET /api/systems       -> [{id, name}] for every systems/<id>/hierarchy.json
  GET /api/hierarchy     -> hierarchy.json (?system=<id>, default uw-medicine)

The UI renders directly from hierarchy.json files — there is no embedded copy.
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

app = FastAPI(title="HS2 Hierarchy Explorer")

SYSTEMS_ROOT = Path(__file__).parent.parent / "systems"
DEFAULT_SYSTEM = "uw-medicine"


def _system_path(system):
    """Resolve a system id to its hierarchy.json, rejecting traversal."""
    if not system or "/" in system or "\\" in system or ".." in system:
        return None
    p = SYSTEMS_ROOT / system / "hierarchy.json"
    try:
        p.resolve().relative_to(SYSTEMS_ROOT.resolve())
    except ValueError:
        return None
    return p if p.exists() else None


@app.get("/api/systems")
def list_systems():
    out = []
    for d in sorted(SYSTEMS_ROOT.iterdir()):
        if not d.is_dir():
            continue
        p = d / "hierarchy.json"
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        out.append({"id": d.name, "name": data.get("health_system", d.name)})
    return out


@app.get("/api/hierarchy")
def get_hierarchy(system: str = Query(DEFAULT_SYSTEM)):
    p = _system_path(system)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Unknown system '{system}'")
    return json.loads(p.read_text())


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8646)
