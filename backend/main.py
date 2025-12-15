# backend/main.py
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
from warehouse_calc import WarehouseCalculator

app = FastAPI(title="Warehouse 3D Visualizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

warehouse_data = {}

class Dimensions(BaseModel):
    length: float
    width: float
    height: float
    unit: str = "cm"

class Position(BaseModel):
    floor: int
    row: int
    col: int

class PalletConfig(BaseModel):
    type: str
    weight: float
    length_cm: float 
    width_cm: float
    height_cm: float
    color: str = "#8B4513"
    position: Position

class RackConfig(BaseModel):
    num_floors: int
    num_rows: int
    num_racks: int
    custom_gaps: List[float] = []
    gap_front: float
    gap_back: float
    gap_left: float
    gap_right: float
    wall_gap_unit: str = "cm"

class BlockConfig(BaseModel):
    block_index: int
    rack_config: RackConfig
    pallet_configs: List[PalletConfig]

class WarehouseConfig(BaseModel):
    id: str
    warehouse_dimensions: Dimensions
    num_blocks: int
    block_gap: float
    block_gap_unit: str = "cm"
    block_configs: List[BlockConfig]

@app.post("/api/warehouse/create")
async def create_warehouse(config: WarehouseConfig):
    try:
        calc = WarehouseCalculator()
        config_dict = config.model_dump()
        layout = calc.create_warehouse_layout(config_dict)
        warehouse_data[config.id] = {"config": config_dict, "layout": layout}
        
        print("\n" + "="*50)
        print(f" NEW WAREHOUSE CREATED: {config.id}")
        print("="*50)
        print(json.dumps(config_dict, indent=2))
        print("="*50 + "\n")

        return {"success": True, "warehouse_id": config.id, "layout": layout}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/warehouse/validate")
async def validate_config(config: WarehouseConfig):
    try:
        calc = WarehouseCalculator()
        calc.create_warehouse_layout(config.model_dump())
        return {"valid": True, "message": "Configuration is valid."}
    except Exception as e:
        return {"valid": False, "message": f"Validation Failed: {str(e)}"}

@app.get("/api/warehouse/{warehouse_id}")
async def get_warehouse(warehouse_id: str):
    if warehouse_id not in warehouse_data:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return {"success": True, "warehouse": warehouse_data[warehouse_id]}

@app.delete("/api/warehouse/{warehouse_id}/delete")
async def delete_warehouse(warehouse_id: str):
    if warehouse_id in warehouse_data:
        deleted_config = warehouse_data[warehouse_id]["config"]
        del warehouse_data[warehouse_id]
        
        print("\n" + "!"*50)
        print(f" WAREHOUSE DELETED: {warehouse_id}")
        print("!"*50)
        print(json.dumps(deleted_config, indent=2))
        print("!"*50 + "\n")

        return {"success": True, "message": f"Warehouse {warehouse_id} deleted."}
    raise HTTPException(status_code=404, detail="Warehouse not found")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)