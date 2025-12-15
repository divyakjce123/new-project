# frontend/warehouse_visualizer.py (UPDATED VERSION)
import dash
from dash import dcc, html, Input, Output, State, ALL, MATCH, ctx, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests
import json
from typing import List, Dict, Any
import uuid

# Initialize the app
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
                suppress_callback_exceptions=True)
server = app.server

# Backend API URL
BACKEND_URL = "http://127.0.0.1:5000"

# --- Helper Functions ---
def to_cm(value, unit):
    """Converts various length units to centimeters."""
    if value is None or value == '':
        return 0
    try:
        val = float(value)
    except ValueError:
        return 0
    
    unit = unit.lower()
    if unit == 'mm': return val / 10.0
    elif unit == 'cm': return val
    elif unit == 'm': return val * 100.0
    elif unit == 'ft': return val * 30.48
    elif unit == 'in': return val * 2.54
    return val

def create_cube_vertices(x0, y0, z0, width, length, height):
    """Create vertices for a 3D cube."""
    x1, y1, z1 = x0 + width, y0 + length, z0 + height
    
    vertices = {
        'x': [x0, x1, x1, x0, x0, x1, x1, x0],
        'y': [y0, y0, y1, y1, y0, y0, y1, y1],
        'z': [z0, z0, z0, z0, z1, z1, z1, z1]
    }
    
    # Define triangles for the cube (12 triangles)
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 7]
    k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]
    
    return {'x': vertices['x'], 'y': vertices['y'], 'z': vertices['z'], 'i': i, 'j': j, 'k': k}

def length_unit_dropdown(id_name, default_val='cm'):
    return dbc.Select(
        id=id_name,
        options=[
            {"label": "mm", "value": "mm"},
            {"label": "cm", "value": "cm"},
            {"label": "m", "value": "m"},
            {"label": "ft", "value": "ft"},
            {"label": "in", "value": "in"},
        ],
        value=default_val,
        className="form-select-sm",
        size="sm"
    )

def weight_unit_dropdown(id_name, default_val='kg'):
    return dbc.Select(
        id=id_name,
        options=[
            {"label": "kg", "value": "kg"},
            {"label": "lbs", "value": "lbs"},
            {"label": "tons", "value": "tons"},
        ],
        value=default_val,
        className="form-select-sm",
        size="sm"
    )

def input_with_unit(label, input_id, unit_id, default_input_val, unit_type='length', default_unit_val='cm'):
    """Helper to create a row with label, input, and unit dropdown."""
    unit_dd = length_unit_dropdown(unit_id, default_unit_val) if unit_type == 'length' else weight_unit_dropdown(unit_id, default_unit_val)
    
    return dbc.Row([
        dbc.Col(dbc.Label(label, className="col-form-label-sm fw-bold"), width=5),
        dbc.Col(dbc.Input(id=input_id, type="number", value=default_input_val, 
                         className="form-control-sm", size="sm", min=0), width=4),
        dbc.Col(unit_dd, width=3),
    ], className="mb-2 align-items-center")

# --- Warehouse Dimensions Card ---
warehouse_dims_card = dbc.Card([
    dbc.CardHeader("Warehouse Dimensions", className="fw-bold"),
    dbc.CardBody([
        input_with_unit("Length", "warehouse-length", "warehouse-length-unit", 3000, 'length', 'cm'),
        input_with_unit("Width", "warehouse-width", "warehouse-width-unit", 2000, 'length', 'cm'),
        input_with_unit("Height", "warehouse-height", "warehouse-height-unit", 800, 'length', 'cm'),
    ])
], className="mb-3")

# --- Blocks Configuration Card ---
blocks_config_card = dbc.Card([
    dbc.CardHeader("Blocks Configuration", className="fw-bold"),
    dbc.CardBody([
        dbc.Row([
            dbc.Col(dbc.Label("Number of Blocks", className="fw-bold"), width=6),
            dbc.Col(dbc.Input(id="num-blocks", type="number", value=2, min=1, max=10, 
                             className="form-control-sm", size="sm"), width=6),
        ], className="mb-3"),
        input_with_unit("Gap Between Blocks", "block-gap", "block-gap-unit", 300, 'length', 'cm'),
        html.Hr(),
        html.Div(id="blocks-container", className="mt-3"),
    ])
], className="mb-3")

# --- Layout Controls Card ---
controls_card = dbc.Card([
    dbc.CardHeader("Visualization Controls", className="fw-bold"),
    dbc.CardBody([
        dbc.ButtonGroup([
            dbc.Button([html.I(className="fas fa-cube me-2"), "3D View"], 
                      id="btn-3d", color="primary", className="w-50"),
            dbc.Button([html.I(className="fas fa-square me-2"), "2D View"], 
                      id="btn-2d", color="secondary", className="w-50", outline=True),
        ], className="w-100 mb-3"),
        dbc.Button([html.I(className="fas fa-sync-alt me-2"), "Generate Layout"], 
                  id="btn-generate", color="success", className="w-100 mb-2"),
        dbc.Button([html.I(className="fas fa-trash me-2"), "Clear"], 
                  id="btn-clear", color="warning", className="w-100"),
    ])
])

# --- Status Card ---
status_card = dbc.Card([
    dbc.CardHeader("Status", className="fw-bold"),
    dbc.CardBody([
        html.Div(id="status-text", children="Ready to generate layout", className="small"),
        html.Hr(),
        html.Div([
            html.Small("Warehouse ID:", className="text-muted"),
            dbc.Input(id="warehouse-id", value="warehouse_1", size="sm", className="mt-1")
        ])
    ])
])

# --- Main Layout ---
sidebar = html.Div([
    warehouse_dims_card,
    blocks_config_card,
    controls_card,
    status_card
], style={"maxHeight": "95vh", "overflowY": "auto", "padding": "1px"})

main_content = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("3D Warehouse Visualizer", 
                        className="text-center text-primary my-3"), width=12)
    ]),
    dbc.Row([
        dbc.Col(sidebar, width=3, className="bg-light border-end"),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("3D Warehouse Visualization", className="fw-bold"),
                dbc.CardBody([
                    dcc.Loading(
                        dcc.Graph(id="warehouse-graph", 
                                 style={"height": "70vh", "width": "100%"},
                                 config={'displayModeBar': True}),
                        type="circle"
                    )
                ])
            ], className="shadow-sm")
        ], width=9)
    ])
], fluid=True)

app.layout = main_content

# --- Pallet Configuration Template ---
def create_pallet_config(pallet_idx, block_idx):
    """Create a pallet configuration row."""
    return html.Div([
        html.Hr(className="my-2"),
        dbc.Row([
            dbc.Col(html.Small(f"Pallet {pallet_idx + 1}", className="fw-bold text-primary"), width=12),
        ], className="mb-1"),
        
        # Pallet Configuration
        dbc.Row([
            dbc.Col(dbc.Label("Pallet Type", className="small"), width=4),
            dbc.Col(dbc.Select(
                id={'type': 'pallet-type', 'index': f"{block_idx}-{pallet_idx}"},
                options=[
                    {"label": "Wooden", "value": "wooden"},
                    {"label": "Plastic", "value": "plastic"},
                    {"label": "Metal", "value": "metal"},
                    {"label": "Euro Pallet", "value": "euro"},
                    {"label": "Display Pallet", "value": "display"},
                ],
                value="wooden",
                className="form-select-sm",
                size="sm"
            ), width=8),
        ], className="mb-1"),
        
        dbc.Row([
            dbc.Col(dbc.Label("Length", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'pallet-length', 'index': f"{block_idx}-{pallet_idx}"},
                            type="number", value=120, size="sm"), width=4),
            dbc.Col(length_unit_dropdown({'type': 'pallet-length-unit', 'index': f"{block_idx}-{pallet_idx}"}, 'cm'), width=4),
        ], className="mb-1 align-items-center"),
        
        dbc.Row([
            dbc.Col(dbc.Label("Width", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'pallet-width', 'index': f"{block_idx}-{pallet_idx}"},
                            type="number", value=80, size="sm"), width=4),
            dbc.Col(length_unit_dropdown({'type': 'pallet-width-unit', 'index': f"{block_idx}-{pallet_idx}"}, 'cm'), width=4),
        ], className="mb-1 align-items-center"),
        
        dbc.Row([
            dbc.Col(dbc.Label("Height", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'pallet-height', 'index': f"{block_idx}-{pallet_idx}"},
                            type="number", value=15, size="sm"), width=4),
            dbc.Col(length_unit_dropdown({'type': 'pallet-height-unit', 'index': f"{block_idx}-{pallet_idx}"}, 'cm'), width=4),
        ], className="mb-1 align-items-center"),
        
        dbc.Row([
            dbc.Col(dbc.Label("Weight", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'pallet-weight', 'index': f"{block_idx}-{pallet_idx}"},
                            type="number", value=500, size="sm"), width=4),
            dbc.Col(weight_unit_dropdown({'type': 'pallet-weight-unit', 'index': f"{block_idx}-{pallet_idx}"}, 'kg'), width=4),
        ], className="mb-2 align-items-center"),
        
        # Pallet Position
        html.H6("Pallet Position", className="mt-3 fw-bold text-primary"),
        dbc.Row([
            dbc.Col(dbc.Label("Floor", className="small"), width=6),
            dbc.Col(dbc.Input(id={'type': 'pallet-floor', 'index': f"{block_idx}-{pallet_idx}"},
                            type="number", value=1, min=1, size="sm"), width=6),
            dbc.Col(dbc.Label("Row", className="small"), width=6),
            dbc.Col(dbc.Input(id={'type': 'pallet-row', 'index': f"{block_idx}-{pallet_idx}"},
                            type="number", value=1, min=1, size="sm"), width=6),
            dbc.Col(dbc.Label("Rack", className="small"), width=6),
            dbc.Col(dbc.Input(id={'type': 'pallet-rack', 'index': f"{block_idx}-{pallet_idx}"},
                            type="number", value=1, min=1, size="sm"), width=6),

        ], className="mb-1"),

        
        # Remove button
        dbc.Row([
            dbc.Col(dbc.Button("Remove", id={'type': 'remove-pallet', 'index': f"{block_idx}-{pallet_idx}"},
                             color="danger", size="sm", className="w-100"), width=12)
        ], className="mb-2")
    ], id={'type': 'pallet-config', 'index': f"{block_idx}-{pallet_idx}"},
       className="border rounded p-2 mb-2 bg-light")

# --- Block Configuration Template ---
def create_block_config(block_index):
    """Create a block configuration card with racks and pallet settings."""
    return dbc.AccordionItem ([ 
        # Racks Configuration
        html.H6("Racks Configuration", className="mt-2 fw-bold text-primary"),
        
        # Basic rack dimensions
        dbc.Row([
            dbc.Col(dbc.Label("Number of Floors", className="small fw-bold"), width=6),
            dbc.Col(dbc.Input(id={'type': 'rack-floors', 'index': block_index}, 
                             type="number", value=3, min=1, size="sm"), width=6),
        ], className="mb-2"),
        
        dbc.Row([
            dbc.Col(dbc.Label("Number of Rows", className="small fw-bold"), width=6),
            dbc.Col(dbc.Input(id={'type': 'rack-rows', 'index': block_index}, 
                             type="number", value=2, min=1, size="sm"), width=6),
        ], className="mb-2"),
        
        dbc.Row([
            dbc.Col(dbc.Label("Number of Racks", className="small fw-bold"), width=6),
            dbc.Col(dbc.Input(id={'type': 'rack-count', 'index': block_index}, 
                             type="number", value=4, min=1, size="sm"), width=6),
        ], className="mb-3"),

        # Rack Gaps
        html.H6("Rack Gaps", className="mt-3 fw-bold text-primary"),

        html.Div([
            dbc.Row([
                dbc.Col(
                    dbc.Label(f"Gap between Rack {i+1}-{i+2}", className="small"),
            width=5
                ),
                dbc.Col(
                    dbc.Input(
                        id={'type': 'rack-gap', 'index': f"{block_index}-{i}"},
                        type="number",
                        value=20,
                        min=0,
                        size="sm"
                    ),
                    width=4
                ),
                dbc.Col(
                    length_unit_dropdown(
                        {'type': 'rack-gap-unit', 'index': f"{block_index}-{i}"},
                        'cm'
                    )        ,
                    width=3
                ),
            ], className="mb-1 align-items-center")
            for i in range(3)   # default: rack 1-2, 2-3, 3-4
        ]),


        
        # Wall gaps
        html.H6("Wall Gaps", className="mt-3 fw-bold text-primary"),
        dbc.Row([
            dbc.Col(dbc.Label("Front Wall Gap", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'gap-front', 'index': block_index}, 
                             type="number", value=100, min=0, size="sm"), width=4),
            dbc.Col(length_unit_dropdown({'type': 'gap-front-unit', 'index': block_index}, 'cm'), width=4),
        ], className="mb-1"),
        
        dbc.Row([
            dbc.Col(dbc.Label("Back Wall Gap", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'gap-back', 'index': block_index}, 
                             type="number", value=100, min=0, size="sm"), width=4),
            dbc.Col(length_unit_dropdown({'type': 'gap-back-unit', 'index': block_index}, 'cm'), width=4),
        ], className="mb-1"),
        
        dbc.Row([
            dbc.Col(dbc.Label("Left Wall Gap", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'gap-left', 'index': block_index}, 
                             type="number", value=50, min=0, size="sm"), width=4),
            dbc.Col(length_unit_dropdown({'type': 'gap-left-unit', 'index': block_index}, 'cm'), width=4),
        ], className="mb-1"),
        
        dbc.Row([
            dbc.Col(dbc.Label("Right Wall Gap", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'gap-right', 'index': block_index}, 
                             type="number", value=50, min=0, size="sm"), width=4),
            dbc.Col(length_unit_dropdown({'type': 'gap-right-unit', 'index': block_index}, 'cm'), width=4),
        ], className="mb-3"),
        
        html.Hr(),
        
        # Pallet Configuration Section
        html.Div([
            html.H6("Pallet Configuration", className="mt-3 fw-bold text-success"),
            dbc.Button([html.I(className="fas fa-plus me-1"), "Add Pallet"], 
                      id={'type': 'add-pallet', 'index': block_index},
                      color="success", size="sm", className="mb-3"),
            html.Div(id={'type': 'pallets-container', 'index': block_index}, className="mt-2")
        ])
        
    ], title=f"Block {block_index + 1} Configuration", item_id=f"block-{block_index}")


# --- Callbacks ---

# 1. Generate dynamic block cards
@app.callback(
    Output("blocks-container", "children"),
    Input("num-blocks", "value")
)
def update_blocks_container(num_blocks):
    if num_blocks is None or num_blocks < 1:
        return []
    
    accordion_items = []
    for i in range(num_blocks):
        accordion_items.append(create_block_config(i))
    
    return dbc.Accordion(accordion_items, always_open=True, active_item=[f"block-{i}" for i in range(num_blocks)])

# 2. Generate dynamic rack gap inputs
@app.callback(
    Output({'type': 'rack-gaps-container', 'index': MATCH}, 'children'),
    Input({'type': 'rack-count', 'index': MATCH}, 'value')
)
def update_rack_gaps_inputs(num_racks):
    block_index = MATCH['index']
    if num_racks is None or num_racks < 2:
        return html.Small("No gaps needed for single rack", className="text-muted fst-italic")
    
    gaps_container = [
        html.H6("Gaps Between Racks", className="small fw-bold text-dark mt-2"),
    ]
    
    for i in range(num_racks - 1):
        gaps_container.append(
            dbc.Row([
                dbc.Col(dbc.Label(f"Gap between Rack {i+1}-{i+2}", className="small"), width=5),
                dbc.Col(dbc.Input(id={'type': 'rack-gap', 'index': f"{block_index}-{i}"}, 
                                 type="number", value=20, min=0, size="sm"), width=4),
                dbc.Col(length_unit_dropdown({'type': 'rack-gap-unit', 'index': f"{block_index}-{i}"}, 'cm'), width=3),
            ], className="mb-1 align-items-center")
        )
    
    return html.Div(gaps_container)

# 3. Add/remove pallets
@app.callback(
    Output({'type': 'pallets-container', 'index': MATCH}, 'children'),
    [Input({'type': 'add-pallet', 'index': MATCH}, 'n_clicks'),
     Input({'type': 'remove-pallet', 'index': ALL}, 'n_clicks')],
    [State({'type': 'pallets-container', 'index': MATCH}, 'children'),
     State({'type': 'add-pallet', 'index': MATCH}, 'id')]
)
def manage_pallets(add_clicks, remove_clicks, current_children, button_id):
    ctx_triggered = ctx.triggered_id
    block_idx = button_id['index']
    
    if current_children is None:
        current_children = []
    
    # Initialize pallet count
    if not current_children:
        pallet_count = 0
    else:
        # Count existing pallets
        pallet_count = len(current_children)
    
    # Add pallet
    if ctx_triggered and ctx_triggered['type'] == 'add-pallet':
        new_pallet = create_pallet_config(pallet_count, block_idx)
        if isinstance(current_children, list):
            return current_children + [new_pallet]
        else:
            return [new_pallet]
    
    # Remove pallet
    elif ctx_triggered and ctx_triggered['type'] == 'remove-pallet':
        pallet_to_remove = ctx_triggered['index']
        
        # Parse the pallet index to remove
        if isinstance(current_children, list):
            # Find and remove the pallet
            updated_children = []
            for child in current_children:
                if 'props' in child and 'id' in child['props']:
                    if child['props']['id']['index'] != pallet_to_remove:
                        updated_children.append(child)
            return updated_children
    
    return current_children

# 4. Toggle 2D/3D view
@app.callback(
    [Output("btn-2d", "outline"), Output("btn-3d", "outline"),
     Output("btn-2d", "color"), Output("btn-3d", "color")],
    [Input("btn-2d", "n_clicks"), Input("btn-3d", "n_clicks")],
    [State("btn-2d", "outline"), State("btn-3d", "outline")]
)
def toggle_view_mode(n2d, n3d, btn2d_outline, btn3d_outline):
    ctx_triggered = ctx.triggered_id
    if ctx_triggered == "btn-2d":
        return False, True, "primary", "secondary"
    elif ctx_triggered == "btn-3d":
        return True, False, "secondary", "primary"
    return btn2d_outline, btn3d_outline, "secondary", "primary"

# 5. Main layout generation callback
@app.callback(
    [Output("warehouse-graph", "figure"),
     Output("status-text", "children")],
    [Input("btn-generate", "n_clicks"),
     Input("btn-clear", "n_clicks")],
    [State("warehouse-length", "value"), State("warehouse-length-unit", "value"),
     State("warehouse-width", "value"), State("warehouse-width-unit", "value"),
     State("warehouse-height", "value"), State("warehouse-height-unit", "value"),
     State("num-blocks", "value"),
     State("block-gap", "value"), State("block-gap-unit", "value"),
     State("warehouse-id", "value"),
     State("btn-3d", "outline"),
     # Dynamic states for all blocks
     State({'type': 'rack-floors', 'index': ALL}, 'value'),
     State({'type': 'rack-rows', 'index': ALL}, 'value'),
     State({'type': 'rack-count', 'index': ALL}, 'value'),
     State({'type': 'gap-front', 'index': ALL}, 'value'),
     State({'type': 'gap-front-unit', 'index': ALL}, 'value'),
     State({'type': 'gap-back', 'index': ALL}, 'value'),
     State({'type': 'gap-back-unit', 'index': ALL}, 'value'),
     State({'type': 'gap-left', 'index': ALL}, 'value'),
     State({'type': 'gap-left-unit', 'index': ALL}, 'value'),
     State({'type': 'gap-right', 'index': ALL}, 'value'),
     State({'type': 'gap-right-unit', 'index': ALL}, 'value'),
     # Rack gaps
     State({'type': 'rack-gap', 'index': ALL}, 'value'),
     State({'type': 'rack-gap-unit', 'index': ALL}, 'value'),
     State({'type': 'rack-gap', 'index': ALL}, 'id'),
     # Pallets
     State({'type': 'pallets-container', 'index': ALL}, 'children')],
    prevent_initial_call=True
)
def generate_or_clear_layout(generate_clicks, clear_clicks,
                            wl, wlu, ww, wwu, wh, whu,
                            num_blocks, block_gap, block_gap_unit,
                            warehouse_id, is_3d_active,
                            rack_floors_list, rack_rows_list, rack_count_list,
                            gap_front_list, gap_front_unit_list,
                            gap_back_list, gap_back_unit_list,
                            gap_left_list, gap_left_unit_list,
                            gap_right_list, gap_right_unit_list,
                            rack_gap_values, rack_gap_units, rack_gap_ids,
                            pallets_containers):
    
    ctx_triggered = ctx.triggered_id
    
    # Clear button clicked
    if ctx_triggered == "btn-clear":
        empty_fig = go.Figure(layout={
            'title': 'Warehouse Layout',
            'scene' if not is_3d_active else 'xaxis': {'title': 'X (cm)'},
            'yaxis': {'title': 'Y (cm)'},
            'margin': {'l': 0, 'r': 0, 't': 30, 'b': 0}
        })
        return empty_fig, "Layout cleared"
    
    # Generate button clicked
    try:
        # Convert all dimensions to centimeters
        warehouse_length_cm = to_cm(wl, wlu)
        warehouse_width_cm = to_cm(ww, wwu)
        warehouse_height_cm = to_cm(wh, whu)
        block_gap_cm = to_cm(block_gap, block_gap_unit)
        
        # Create figure
        fig = go.Figure()
        
        # Determine if 3D view is active
        is_3d = not is_3d_active
        
        # Calculate block dimensions
        total_block_gaps = block_gap_cm * (num_blocks - 1) if num_blocks > 1 else 0
        total_block_width = warehouse_width_cm - total_block_gaps
        block_width = total_block_width / num_blocks
        block_length = warehouse_length_cm
        
        # Starting position for blocks
        start_x = -warehouse_width_cm / 2 + block_width / 2
        
        # Colors for different pallet types
        pallet_colors = {
            'wooden': '#8B4513',    # SaddleBrown
            'plastic': '#1E90FF',   # DodgerBlue
            'metal': '#C0C0C0',     # Silver
            'euro': '#32CD32',      # LimeGreen
            'display': '#FFD700'    # Gold
        }
        
        # Store all pallets for backend
        all_pallets = []
        
        # Process each block
        for block_idx in range(num_blocks):
            # Block position
            block_x = start_x + block_idx * (block_width + block_gap_cm)
            
            # Draw block boundary
            if is_3d:
                # 3D block boundary
                block_points = create_cube_vertices(
                    block_x - block_width/2, 0, 0,
                    block_width, block_length, warehouse_height_cm
                )
                fig.add_trace(go.Mesh3d(
                    x=block_points['x'],
                    y=block_points['y'],
                    z=block_points['z'],
                    i=block_points['i'],
                    j=block_points['j'],
                    k=block_points['k'],
                    opacity=0.1,
                    color='rgba(200, 200, 200, 0.2)',
                    name=f'Block {block_idx+1} Boundary',
                    hoverinfo='name',
                    showlegend=True
                ))
            else:
                # 2D block boundary
                x_coords = [block_x - block_width/2, block_x + block_width/2, 
                           block_x + block_width/2, block_x - block_width/2, 
                           block_x - block_width/2]
                y_coords = [0, 0, block_length, block_length, 0]
                fig.add_trace(go.Scatter(
                    x=x_coords,
                    y=y_coords,
                    mode='lines',
                    line=dict(color='blue', width=2, dash='dash'),
                    name=f'Block {block_idx+1} Boundary',
                    hoverinfo='name'
                ))
            
            # Add block label
            label_x = block_x
            label_y = block_length / 2
            label_z = warehouse_height_cm + 50  # Above the block
            
            if is_3d:
                fig.add_trace(go.Scatter3d(
                    x=[label_x],
                    y=[label_y],
                    z=[label_z],
                    mode='text',
                    text=[f'Block {block_idx+1}'],
                    textposition='middle center',
                    textfont=dict(size=14, color='blue'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=[label_x],
                    y=[label_y],
                    mode='text',
                    text=[f'Block {block_idx+1}'],
                    textposition='middle center',
                    textfont=dict(size=12, color='blue'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            
            # Get block configuration
            if block_idx < len(rack_floors_list):
                # Calculate rack dimensions and positions within block
                rack_floors = rack_floors_list[block_idx] or 1
                rack_rows = rack_rows_list[block_idx] or 1
                rack_count = rack_count_list[block_idx] or 1
                
                # Convert wall gaps to cm
                gap_front = to_cm(gap_front_list[block_idx] or 0, gap_front_unit_list[block_idx])
                gap_back = to_cm(gap_back_list[block_idx] or 0, gap_back_unit_list[block_idx])
                gap_left = to_cm(gap_left_list[block_idx] or 0, gap_left_unit_list[block_idx])
                gap_right = to_cm(gap_right_list[block_idx] or 0, gap_right_unit_list[block_idx])
                
                # Calculate available space for racks
                available_length = block_length - gap_front - gap_back
                available_width = block_width - gap_left - gap_right
                
                # Calculate rack dimensions
                rack_length = available_length / rack_rows
                racks_per_row = rack_count // rack_rows
                if rack_count % rack_rows != 0:
                    racks_per_row += 1
                
                # Calculate rack gaps for this block
                block_gaps = []
                if rack_gap_ids:
                    for gap_id_dict in rack_gap_ids:
                        if gap_id_dict and 'index' in gap_id_dict:
                            if str(block_idx) in gap_id_dict['index']:
                                parts = gap_id_dict['index'].split('-')
                                if len(parts) >= 2:
                                    gap_index_in_block = int(parts[-1])
                                    gap_list_index = rack_gap_ids.index(gap_id_dict)
                                    if gap_list_index < len(rack_gap_values):
                                        gap_value = rack_gap_values[gap_list_index] or 0
                                        gap_unit = rack_gap_units[gap_list_index] if gap_list_index < len(rack_gap_units) else 'cm'
                                        block_gaps.append(to_cm(gap_value, gap_unit))
                
                # Calculate total gaps width
                total_gaps_width = sum(block_gaps[:racks_per_row-1]) if racks_per_row > 1 else 0
                
                # Calculate rack width
                rack_width = (available_width - total_gaps_width) / racks_per_row
                floor_height = warehouse_height_cm / rack_floors
                
                # Create racks
                rack_global_idx = 0
                for row_idx in range(rack_rows):
                    for col_idx in range(racks_per_row):
                        if rack_global_idx >= rack_count:
                            break
                        
                        # Calculate rack position
                        rack_x = block_x - block_width/2 + gap_left + col_idx * rack_width
                        if col_idx > 0:
                            rack_x += sum(block_gaps[:col_idx])
                        rack_x += rack_width / 2
                        
                        rack_y = gap_front + row_idx * rack_length + rack_length / 2
                        
                        # Create each floor of the rack
                        for floor_idx in range(rack_floors):
                            rack_z = floor_idx * floor_height + floor_height / 2
                            
                            # Draw rack
                            if is_3d:
                                rack_points = create_cube_vertices(
                                    rack_x - rack_width/2, rack_y - rack_length/2, rack_z - floor_height/2,
                                    rack_width, rack_length, floor_height
                                )
                                fig.add_trace(go.Mesh3d(
                                    x=rack_points['x'],
                                    y=rack_points['y'],
                                    z=rack_points['z'],
                                    i=rack_points['i'],
                                    j=rack_points['j'],
                                    k=rack_points['k'],
                                    opacity=0.3,
                                    color='#A9A9A9',  # DarkGray for racks
                                    name=f'Rack {rack_global_idx+1}-F{floor_idx+1}',
                                    hoverinfo='name',
                                    showlegend=False
                                ))
                        
                        rack_global_idx += 1
        
        # Set layout properties
        if is_3d:
            fig.update_layout(
                title=f'3D Warehouse Layout - {num_blocks} Blocks',
                scene=dict(
                    xaxis=dict(title='Width (cm)', range=[-warehouse_width_cm/2, warehouse_width_cm/2]),
                    yaxis=dict(title='Length (cm)', range=[0, warehouse_length_cm]),
                    zaxis=dict(title='Height (cm)', range=[0, warehouse_height_cm]),
                    aspectmode='manual',
                    aspectratio=dict(x=2, y=3, z=1)
                ),
                margin=dict(l=0, r=0, t=40, b=0),
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
            )
        else:
            fig.update_layout(
                title=f'2D Warehouse Layout - {num_blocks} Blocks',
                xaxis=dict(
                    title='Width (cm)',
                    range=[-warehouse_width_cm/2, warehouse_width_cm/2],
                    scaleanchor="y",
                    scaleratio=1
                ),
                yaxis=dict(
                    title='Length (cm)',
                    range=[0, warehouse_length_cm]
                ),
                margin=dict(l=0, r=0, t=40, b=0),
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
            )
        
        return fig, f"Layout generated with {num_blocks} blocks"
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_fig = go.Figure(layout={'title': f'Error: {str(e)}'})
        return error_fig, f"Error: {str(e)}"

# 6. Callback to send data to backend API
@app.callback(
    Output("status-text", "children", allow_duplicate=True),
    Input("btn-generate", "n_clicks"),
    [State("warehouse-length", "value"), State("warehouse-length-unit", "value"),
     State("warehouse-width", "value"), State("warehouse-width-unit", "value"),
     State("warehouse-height", "value"), State("warehouse-height-unit", "value"),
     State("num-blocks", "value"),
     State("block-gap", "value"), State("block-gap-unit", "value"),
     State("warehouse-id", "value"),
     # Dynamic states for all blocks
     State({'type': 'rack-floors', 'index': ALL}, 'value'),
     State({'type': 'rack-rows', 'index': ALL}, 'value'),
     State({'type': 'rack-count', 'index': ALL}, 'value'),
     State({'type': 'gap-front', 'index': ALL}, 'value'),
     State({'type': 'gap-front-unit', 'index': ALL}, 'value'),
     State({'type': 'gap-back', 'index': ALL}, 'value'),
     State({'type': 'gap-back-unit', 'index': ALL}, 'value'),
     State({'type': 'gap-left', 'index': ALL}, 'value'),
     State({'type': 'gap-left-unit', 'index': ALL}, 'value'),
     State({'type': 'gap-right', 'index': ALL}, 'value'),
     State({'type': 'gap-right-unit', 'index': ALL}, 'value'),
     # Rack gaps
     State({'type': 'rack-gap', 'index': ALL}, 'value'),
     State({'type': 'rack-gap-unit', 'index': ALL}, 'value'),
     State({'type': 'rack-gap', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def send_to_backend(n_clicks, wl, wlu, ww, wwu, wh, whu, num_blocks, block_gap, block_gap_unit, warehouse_id,
                   rack_floors_list, rack_rows_list, rack_count_list,
                   gap_front_list, gap_front_unit_list,
                   gap_back_list, gap_back_unit_list,
                   gap_left_list, gap_left_unit_list,
                   gap_right_list, gap_right_unit_list,
                   rack_gap_values, rack_gap_units, rack_gap_ids):
    """Send configuration to backend API for processing."""
    try:
        # Prepare configuration data
        config = {
            "id": warehouse_id,
            "warehouse_dimensions": {
                "length": wl,
                "width": ww,
                "height": wh,
                "unit": wlu
            },
            "num_blocks": num_blocks,
            "block_gap": block_gap,
            "block_gap_unit": block_gap_unit,
            "block_configs": []
        }
        
        # Add block configurations
        for block_idx in range(num_blocks):
            block_config = {
                "block_index": block_idx,
                "rack_config": {
                    "floors": rack_floors_list[block_idx] if block_idx < len(rack_floors_list) else 3,
                    "rows": rack_rows_list[block_idx] if block_idx < len(rack_rows_list) else 2,
                    "count": rack_count_list[block_idx] if block_idx < len(rack_count_list) else 4
                },
                "wall_gaps": {
                    "front": gap_front_list[block_idx] if block_idx < len(gap_front_list) else 100,
                    "front_unit": gap_front_unit_list[block_idx] if block_idx < len(gap_front_unit_list) else 'cm',
                    "back": gap_back_list[block_idx] if block_idx < len(gap_back_list) else 100,
                    "back_unit": gap_back_unit_list[block_idx] if block_idx < len(gap_back_unit_list) else 'cm',
                    "left": gap_left_list[block_idx] if block_idx < len(gap_left_list) else 50,
                    "left_unit": gap_left_unit_list[block_idx] if block_idx < len(gap_left_unit_list) else 'cm',
                    "right": gap_right_list[block_idx] if block_idx < len(gap_right_list) else 50,
                    "right_unit": gap_right_unit_list[block_idx] if block_idx < len(gap_right_unit_list) else 'cm'
                },
                "rack_gaps": []
            }
            
            # Add rack gaps for this block
            if rack_gap_ids:
                for gap_id_dict in rack_gap_ids:
                    if gap_id_dict and 'index' in gap_id_dict:
                        if str(block_idx) in gap_id_dict['index']:
                            parts = gap_id_dict['index'].split('-')
                            if len(parts) >= 2:
                                gap_index = int(parts[-1])
                                gap_list_index = rack_gap_ids.index(gap_id_dict)
                                if gap_list_index < len(rack_gap_values):
                                    gap_config = {
                                        "from_rack": gap_index + 1,
                                        "to_rack": gap_index + 2,
                                        "gap": rack_gap_values[gap_list_index] if gap_list_index < len(rack_gap_values) else 20,
                                        "unit": rack_gap_units[gap_list_index] if gap_list_index < len(rack_gap_units) else 'cm'
                                    }
                                    block_config["rack_gaps"].append(gap_config)
            
            config["block_configs"].append(block_config)
        
        # Send to backend
        response = requests.post(
            f"{BACKEND_URL}/api/warehouse/create",
            json=config,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return f"Backend: {result.get('message', 'Success')}. ID: {warehouse_id}"
        else:
            return f"Backend error: {response.text}"
            
    except requests.exceptions.RequestException as e:
        return f"Connection error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True, port=8050, dev_tools_hot_reload=True)