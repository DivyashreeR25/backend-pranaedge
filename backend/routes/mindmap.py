from fastapi import APIRouter, HTTPException
from backend.db.mongo import analysis_collection

router = APIRouter()

from backend.utils.auth import get_current_user
from fastapi import Depends

@router.get("/mindmap")
async def get_mindmap(user_id: str = Depends(get_current_user)):
    analysis = await analysis_collection.find_one({"user_id": user_id})
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Run POST /analyze/{user_id} first"
        )

    connections = analysis.get("mindmap_connections", [])
    wellness_insight = analysis.get("wellness_insight", "")
    primary_concern = analysis.get("primary_concern", "")

    # Build React Flow compatible nodes and edges
    node_names = set()
    for conn in connections:
        node_names.add(conn["from"])
        node_names.add(conn["to"])

    # Assign positions in a circular layout
    import math
    nodes = []
    node_list = list(node_names)
    total = len(node_list)
    for i, name in enumerate(node_list):
        angle = (2 * math.pi * i) / total
        x = 300 + 200 * math.cos(angle)
        y = 300 + 200 * math.sin(angle)
        nodes.append({
            "id": name,
            "data": {"label": name},
            "position": {"x": round(x), "y": round(y)},
            "style": {
                "background": "#4ade80" if name == primary_concern.split()[0] else "#93c5fd",
                "borderRadius": "8px",
                "padding": "10px",
                "fontWeight": "bold"
            }
        })

    edges = []
    for i, conn in enumerate(connections):
        edges.append({
            "id": f"e{i}",
            "source": conn["from"],
            "target": conn["to"],
            "label": conn["label"],
            "animated": True,
            "style": {"stroke": "#f97316"}
        })

    return {
        "status": "success",
        "wellness_insight": wellness_insight,
        "mindmap": {
            "nodes": nodes,
            "edges": edges
        }
    }