# backend/main.py
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from warehouse_calc import WarehouseCalculator

app = FastAPI(title="Warehouse 3D Visualizer API")

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---

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
    length: float
    width: float
    height: float
    unit: str = "cm"
    color: Optional[str] = "#8B4513"
    # --- MODIFIED: Position is now here instead of Stock ---
    position: Position 

# --- MODIFIED: Removed StockConfig Class ---

class RackConfig(BaseModel):
    num_floors: int
    num_rows: int
    num_racks: int
    gap_between_racks: float = 0  # Fallback
    custom_gaps: List[float] = [] # Specific gaps: [gap_1-2, gap_2-3, ...]
    gap_unit: str = "cm"
    
    # Wall gaps
    gap_front: float
    gap_back: float
    gap_left: float
    gap_right: float
    wall_gap_unit: str = "cm"

class BlockConfig(BaseModel):
    block_index: int
    rack_config: RackConfig
    pallet_config: PalletConfig
    # --- MODIFIED: Removed StockConfig ---

class WarehouseConfig(BaseModel):
    id: str
    warehouse_dimensions: Dimensions
    num_blocks: int
    block_gap: float
    block_gap_unit: str = "cm"
    block_configs: List[BlockConfig]

# --- In-Memory Storage ---
warehouse_data = {}

# --- API Endpoints ---

@app.post("/api/warehouse/create")
async def create_warehouse(config: WarehouseConfig):
    """
    Generates a 3D layout based on the provided configuration.
    The config must match the Pydantic models defined above.
    """
    try:
        calc = WarehouseCalculator()
        # Convert Pydantic model to dict for the calculator
        config_dict = config.model_dump()
        
        layout = calc.create_warehouse_layout(config_dict)
        
        warehouse_data[config.id] = {
            "config": config_dict,
            "layout": layout
        }
        
        return {
            "success": True,
            "warehouse_id": config.id,
            "layout": layout
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/warehouse/validate")
async def validate_config(config: WarehouseConfig):
    """
    Extra API: Checks if the configuration is physically possible 
    (e.g., do racks fit in the block?) before generating.
    """
    try:
        calc = WarehouseCalculator()
        # Perform a dry-run calculation
        calc.create_warehouse_layout(config.model_dump())
        return {"valid": True, "message": "Configuration looks good!"}
    except ValueError as e:
        return {"valid": False, "message": str(e)}

@app.get("/api/warehouse/{warehouse_id}")
async def get_warehouse(warehouse_id: str):
    if warehouse_id not in warehouse_data:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return {"success": True, "warehouse": warehouse_data[warehouse_id]}

@app.delete("/api/warehouse/{warehouse_id}/delete")
async def delete_warehouse(warehouse_id: str):
    if warehouse_id in warehouse_data:
        del warehouse_data[warehouse_id]
        return {"success": True}
    raise HTTPException(status_code=404, detail="Warehouse not found")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)

# from fastapi import FastAPI, HTTPException, Body
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field
# from typing import List, Optional, Dict, Any
# from warehouse_calc import WarehouseCalculator

# app = FastAPI(title="Warehouse 3D Visualizer API")

# # Enable CORS for frontend communication
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # --- Data Models (Make the backend understandable and strict) ---

# class Dimensions(BaseModel):
#     length: float
#     width: float
#     height: float
#     unit: str = "cm"

# class Position(BaseModel):
#     floor: int
#     row: int
#     col: int

# class PalletConfig(BaseModel):
#     type: str
#     weight: float
#     length: float
#     width: float
#     height: float
#     unit: str = "cm"
#     color: Optional[str] = "#8B4513"

# # class StockConfig(BaseModel):
# #     type: str
# #     length: float
# #     width: float
# #     height: float
# #     unit: str = "cm"
# #     color: Optional[str] = "#FF0000"
# #     position: Position

# class RackConfig(BaseModel):
#     num_floors: int
#     num_rows: int
#     num_racks: int
#     gap_between_racks: float = 0  # Fallback
#     custom_gaps: List[float] = [] # Specific gaps: [gap_1-2, gap_2-3, ...]
#     gap_unit: str = "cm"
    
#     # Wall gaps
#     gap_front: float
#     gap_back: float
#     gap_left: float
#     gap_right: float
#     wall_gap_unit: str = "cm"

# class BlockConfig(BaseModel):
#     block_index: int
#     rack_config: RackConfig
#     pallet_config: PalletConfig
#     # stock_config: StockConfig

# class WarehouseConfig(BaseModel):
#     id: str
#     warehouse_dimensions: Dimensions
#     num_blocks: int
#     block_gap: float
#     block_gap_unit: str = "cm"
#     block_configs: List[BlockConfig]

# # --- In-Memory Storage ---
# warehouse_data = {}

# # --- API Endpoints ---

# @app.post("/api/warehouse/create")
# async def create_warehouse(config: WarehouseConfig):
#     """
#     Generates a 3D layout based on the provided configuration.
#     The config must match the Pydantic models defined above.
#     """
#     try:
#         calc = WarehouseCalculator()
#         # Convert Pydantic model to dict for the calculator
#         config_dict = config.model_dump()
        
#         layout = calc.create_warehouse_layout(config_dict)
        
#         warehouse_data[config.id] = {
#             "config": config_dict,
#             "layout": layout
#         }
        
#         return {
#             "success": True,
#             "warehouse_id": config.id,
#             "layout": layout
#         }
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=400, detail=str(e))

# @app.post("/api/warehouse/validate")
# async def validate_config(config: WarehouseConfig):
#     """
#     Extra API: Checks if the configuration is physically possible 
#     (e.g., do racks fit in the block?) before generating.
#     """
#     try:
#         calc = WarehouseCalculator()
#         # Perform a dry-run calculation
#         calc.create_warehouse_layout(config.model_dump())
#         return {"valid": True, "message": "Configuration looks good!"}
#     except ValueError as e:
#         return {"valid": False, "message": str(e)}

# @app.get("/api/warehouse/{warehouse_id}")
# async def get_warehouse(warehouse_id: str):
#     if warehouse_id not in warehouse_data:
#         raise HTTPException(status_code=404, detail="Warehouse not found")
#     return {"success": True, "warehouse": warehouse_data[warehouse_id]}

# @app.delete("/api/warehouse/{warehouse_id}/delete")
# async def delete_warehouse(warehouse_id: str):
#     if warehouse_id in warehouse_data:
#         del warehouse_data[warehouse_id]
#         return {"success": True}
#     raise HTTPException(status_code=404, detail="Warehouse not found")

# if __name__ == '__main__':
#     import uvicorn
#     uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)