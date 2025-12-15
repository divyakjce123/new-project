import dash
from dash import dcc, html, Input, Output, State, ALL, MATCH, ctx, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests
import json

# Initialize the app
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
                suppress_callback_exceptions=True)
server = app.server

# Backend API URL
BACKEND_URL = "http://127.0.0.1:5000"

# --- Helper Functions ---
def to_cm(value, unit):
    if value is None or value == '': return 0.0
    try: val = float(value)
    except ValueError: return 0.0
    unit = unit.lower()
    if unit == 'mm': return val / 10.0
    elif unit == 'cm': return val
    elif unit == 'm': return val * 100.0
    elif unit == 'ft': return val * 30.48
    elif unit == 'in': return val * 2.54
    return val

def create_cube_vertices(x0, y0, z0, width, length, height):
    x1, y1, z1 = x0 + width, y0 + length, z0 + height
    return {
        'x': [x0, x1, x1, x0, x0, x1, x1, x0],
        'y': [y0, y0, y1, y1, y0, y0, y1, y1],
        'z': [z0, z0, z0, z0, z1, z1, z1, z1],
        'i': [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        'j': [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 7],
        'k': [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]
    }

def unit_dropdown(id_name, default_val='cm'):
    return dbc.Select(
        id=id_name,
        options=[{"label": u, "value": u} for u in ["cm", "m", "mm", "ft", "in"]],
        value=default_val, size="sm"
    )

def weight_dropdown(id_name, default_val='kg'):
    return dbc.Select(
        id=id_name,
        options=[{"label": "kg", "value": "kg"}, {"label": "lbs", "value": "lbs"}],
        value=default_val, size="sm"
    )

# --- Layout Components ---

warehouse_dims_card = dbc.Card([
    dbc.CardHeader("Warehouse Dimensions", className="fw-bold small"),
    dbc.CardBody([
        dbc.Row([
            dbc.Col(dbc.Label("Length", className="small fw-bold"), width=4),
            dbc.Col(dbc.Input(id="warehouse-length", type="number", value=3000, size="sm"), width=4),
            dbc.Col(unit_dropdown("warehouse-length-unit"), width=4),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(dbc.Label("Width", className="small fw-bold"), width=4),
            dbc.Col(dbc.Input(id="warehouse-width", type="number", value=2000, size="sm"), width=4),
            dbc.Col(unit_dropdown("warehouse-width-unit"), width=4),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(dbc.Label("Height", className="small fw-bold"), width=4),
            dbc.Col(dbc.Input(id="warehouse-height", type="number", value=800, size="sm"), width=4),
            dbc.Col(unit_dropdown("warehouse-height-unit"), width=4),
        ], className="mb-2"),
    ], className="p-2")
], className="mb-2")

blocks_config_card = dbc.Card([
    dbc.CardHeader("Blocks Configuration", className="fw-bold small"),
    dbc.CardBody([
        dbc.Row([
            dbc.Col(dbc.Label("Number of Blocks", className="small fw-bold"), width=6),
            dbc.Col(dbc.Input(id="num-blocks", type="number", value=2, min=1, size="sm"), width=6),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(dbc.Label("Gap Between Blocks", className="small fw-bold"), width=4),
            dbc.Col(dbc.Input(id="block-gap", type="number", value=300, size="sm"), width=4),
            dbc.Col(unit_dropdown("block-gap-unit"), width=4),
        ], className="mb-2"),
        html.Div(id="blocks-container", className="mt-2"),
    ], className="p-2")
], className="mb-2")

controls_card = dbc.Card([
    dbc.CardHeader("Visualization Controls", className="fw-bold small"),
    dbc.CardBody([
        dbc.ButtonGroup([
            dbc.Button("3D View", id="btn-3d", color="primary", size="sm", className="w-50"),
            dbc.Button("2D View", id="btn-2d", color="secondary", outline=True, size="sm", className="w-50"),
        ], className="w-100 mb-2"),
        dbc.Button("Generate Layout", id="btn-generate", color="success", size="sm", className="w-100 mb-1"),
        dbc.Button("Clear", id="btn-clear", color="warning", size="sm", className="w-100"),
    ], className="p-2")
], className="mb-2")

# --- Dynamic Generators ---

def create_pallet_ui(block_idx, pallet_idx):
    return html.Div([
        html.Hr(className="my-1"),
        html.Div(f"Pallet {pallet_idx + 1}", className="small fw-bold text-primary mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Pallet Type", className="small"), width=4),
            dbc.Col(dbc.Select(
                id={'type': 'pallet-type', 'index': f"{block_idx}-{pallet_idx}"},
                options=[{"label": "Wooden", "value": "wooden"}, {"label": "Plastic", "value": "plastic"}, {"label": "Metal", "value": "metal"}], 
                value="wooden", size="sm"
            ), width=8),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Length", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'pallet-len', 'index': f"{block_idx}-{pallet_idx}"}, type="number", value=120, size="sm"), width=4),
            dbc.Col(unit_dropdown({'type': 'pallet-len-unit', 'index': f"{block_idx}-{pallet_idx}"}), width=4),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Width", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'pallet-wid', 'index': f"{block_idx}-{pallet_idx}"}, type="number", value=80, size="sm"), width=4),
            dbc.Col(unit_dropdown({'type': 'pallet-wid-unit', 'index': f"{block_idx}-{pallet_idx}"}), width=4),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Height", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'pallet-hgt', 'index': f"{block_idx}-{pallet_idx}"}, type="number", value=15, size="sm"), width=4),
            dbc.Col(unit_dropdown({'type': 'pallet-hgt-unit', 'index': f"{block_idx}-{pallet_idx}"}), width=4),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Weight", className="small"), width=4),
            dbc.Col(dbc.Input(id={'type': 'pallet-wgt', 'index': f"{block_idx}-{pallet_idx}"}, type="number", value=500, size="sm"), width=4),
            dbc.Col(weight_dropdown({'type': 'pallet-wgt-unit', 'index': f"{block_idx}-{pallet_idx}"}), width=4),
        ], className="mb-1"),
        html.Div("Pallet Position", className="small fw-bold text-primary mt-2 mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Floor", className="small"), width=6),
            dbc.Col(dbc.Input(id={'type': 'pallet-floor', 'index': f"{block_idx}-{pallet_idx}"}, type="number", value=1, min=1, size="sm"), width=6),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Row", className="small"), width=6),
            dbc.Col(dbc.Input(id={'type': 'pallet-row', 'index': f"{block_idx}-{pallet_idx}"}, type="number", value=1, min=1, size="sm"), width=6),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Rack", className="small"), width=6),
            dbc.Col(dbc.Input(id={'type': 'pallet-rack', 'index': f"{block_idx}-{pallet_idx}"}, type="number", value=1, min=1, size="sm"), width=6),
        ], className="mb-2"),
        dbc.Button("Remove", id={'type': 'remove-pallet', 'index': f"{block_idx}-{pallet_idx}"}, color="danger", size="sm", className="w-100 mb-1")
    ], id={'type': 'pallet-card', 'index': f"{block_idx}-{pallet_idx}"}, className="bg-light p-2 border rounded mb-2")

def create_block_config(i):
    return dbc.AccordionItem([
        html.H6("Racks Configuration", className="text-primary fw-bold small mb-2"),
        dbc.Row([
            dbc.Col(dbc.Label("Number of Floors", className="small fw-bold"), width=8),
            dbc.Col(dbc.Input(id={'type': 'rack-floors', 'index': i}, type="number", value=3, min=1, size="sm"), width=4),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Number of Rows", className="small fw-bold"), width=8),
            dbc.Col(dbc.Input(id={'type': 'rack-rows', 'index': i}, type="number", value=2, min=1, size="sm"), width=4),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Number of Racks", className="small fw-bold"), width=8),
            dbc.Col(dbc.Input(id={'type': 'rack-count', 'index': i}, type="number", value=4, min=1, size="sm"), width=4),
        ], className="mb-2"),
        html.H6("Rack Gaps", className="text-primary fw-bold small mt-2 mb-1"),
        html.Div(id={'type': 'rack-gaps-dynamic-container', 'index': i}, className="mb-2"),
        html.H6("Wall Gaps", className="text-primary fw-bold small mt-2 mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Front Wall Gap", className="small"), width=5),
            dbc.Col(dbc.Input(id={'type': 'gap-front', 'index': i}, value=100, type="number", size="sm"), width=4),
            dbc.Col(unit_dropdown({'type': 'gap-front-u', 'index': i}), width=3)
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Back Wall Gap", className="small"), width=5),
            dbc.Col(dbc.Input(id={'type': 'gap-back', 'index': i}, value=100, type="number", size="sm"), width=4),
            dbc.Col(unit_dropdown({'type': 'gap-back-u', 'index': i}), width=3)
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Left Wall Gap", className="small"), width=5),
            dbc.Col(dbc.Input(id={'type': 'gap-left', 'index': i}, value=50, type="number", size="sm"), width=4),
            dbc.Col(unit_dropdown({'type': 'gap-left-u', 'index': i}), width=3)
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dbc.Label("Right Wall Gap", className="small"), width=5),
            dbc.Col(dbc.Input(id={'type': 'gap-right', 'index': i}, value=50, type="number", size="sm"), width=4),
            dbc.Col(unit_dropdown({'type': 'gap-right-u', 'index': i}), width=3)
        ], className="mb-2"),
        html.Hr(),
        html.H6("Pallet Configuration", className="text-success fw-bold small mb-1"),
        dbc.Button("+ Add Pallet", id={'type': 'add-pallet', 'index': i}, color="success", size="sm", className="mb-2"),
        html.Div(id={'type': 'pallets-container', 'index': i})
    ], title=f"Block {i+1} Configuration", item_id=f"block-{i}")

# --- Main Layout ---
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H3("3D Warehouse Visualizer", className="text-center text-primary my-3"))),
    dbc.Row([
        dbc.Col([
            html.Div([
                warehouse_dims_card,
                blocks_config_card,
                controls_card,
                dbc.Card([dbc.CardBody(html.Div(id="status-text", className="small text-muted"))], className="mt-2")
            ], style={"maxHeight": "90vh", "overflowY": "auto", "paddingRight": "5px"})
        ], width=3, className="bg-light border-end"),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("3D Warehouse Visualization", className="fw-bold small"),
                dbc.CardBody(dcc.Graph(id="warehouse-graph", style={"height": "80vh"}))
            ])
        ], width=9)
    ])
], fluid=True)

# --- Callbacks ---

@app.callback(Output("blocks-container", "children"), Input("num-blocks", "value"))
def update_blocks(n):
    if not n or n < 1: return []
    return dbc.Accordion([create_block_config(i) for i in range(n)], always_open=True, active_item=[f"block-{i}" for i in range(n)])

@app.callback(
    Output({'type': 'rack-gaps-dynamic-container', 'index': MATCH}, 'children'),
    Input({'type': 'rack-count', 'index': MATCH}, 'value')
)
def update_rack_gaps(n_racks):
    block_idx = ctx.triggered_id['index'] if ctx.triggered_id else None
    if not n_racks or n_racks < 2: return html.Div("At least 2 racks required for gaps", className="small text-muted")
    return [dbc.Row([
        dbc.Col(dbc.Label(f"Gap between Rack {i+1}-{i+2}", className="small"), width=5),
        dbc.Col(dbc.Input(id={'type': 'rack-gap-input', 'index': f"{block_idx}-{i}"}, value=20, type="number", size="sm"), width=4),
        dbc.Col(unit_dropdown({'type': 'rack-gap-unit', 'index': f"{block_idx}-{i}"}), width=3),
    ], className="mb-1 align-items-center") for i in range(n_racks - 1)]

@app.callback(
    Output({'type': 'pallets-container', 'index': MATCH}, 'children'),
    [Input({'type': 'add-pallet', 'index': MATCH}, 'n_clicks'),
     Input({'type': 'remove-pallet', 'index': ALL}, 'n_clicks')],
    [State({'type': 'pallets-container', 'index': MATCH}, 'children'),
     State({'type': 'add-pallet', 'index': MATCH}, 'id')]
)
def manage_pallets(add_click, remove_click, children, btn_id):
    trigger = ctx.triggered_id
    if not children: children = []
    if trigger == {'type': 'add-pallet', 'index': btn_id['index']}:
        return children + [create_pallet_ui(btn_id['index'], len(children))]
    if isinstance(trigger, dict) and trigger['type'] == 'remove-pallet':
        return [c for c in children if c['props']['id']['index'] != trigger['index']]
    return children

@app.callback(
    [Output("btn-3d", "outline"), Output("btn-3d", "color"),
     Output("btn-2d", "outline"), Output("btn-2d", "color")],
    [Input("btn-3d", "n_clicks"), Input("btn-2d", "n_clicks")]
)
def toggle_view(n3, n2):
    if ctx.triggered_id == "btn-2d": return True, "secondary", False, "primary"
    return False, "primary", True, "secondary"

# --- Main Generator Callback (CORRECTED ORDER) ---
@app.callback(
    Output("warehouse-graph", "figure"),
    Input("btn-generate", "n_clicks"),
    Input("btn-clear", "n_clicks"),
    State("btn-3d", "outline"),
    
    # 1. Warehouse Dims
    State("warehouse-length", "value"), State("warehouse-length-unit", "value"),
    State("warehouse-width", "value"), State("warehouse-width-unit", "value"),
    State("warehouse-height", "value"), State("warehouse-height-unit", "value"),
    State("num-blocks", "value"), State("block-gap", "value"), State("block-gap-unit", "value"),
    
    # 2. Block Basic Configs
    State({'type': 'rack-floors', 'index': ALL}, 'value'),
    State({'type': 'rack-rows', 'index': ALL}, 'value'),
    State({'type': 'rack-count', 'index': ALL}, 'value'),

    # 3. RACK GAPS (This comes BEFORE Wall Gaps in the decorators list below)
    State({'type': 'rack-gap-input', 'index': ALL}, 'value'),
    State({'type': 'rack-gap-unit', 'index': ALL}, 'value'),
    State({'type': 'rack-gap-input', 'index': ALL}, 'id'), 
    
    # 4. WALL GAPS
    State({'type': 'gap-front', 'index': ALL}, 'value'), State({'type': 'gap-front-u', 'index': ALL}, 'value'),
    State({'type': 'gap-back', 'index': ALL}, 'value'), State({'type': 'gap-back-u', 'index': ALL}, 'value'),
    State({'type': 'gap-left', 'index': ALL}, 'value'), State({'type': 'gap-left-u', 'index': ALL}, 'value'),
    State({'type': 'gap-right', 'index': ALL}, 'value'), State({'type': 'gap-right-u', 'index': ALL}, 'value'),
    
    # 5. PALLETS
    State({'type': 'pallet-type', 'index': ALL}, 'value'),
    State({'type': 'pallet-len', 'index': ALL}, 'value'), State({'type': 'pallet-len-unit', 'index': ALL}, 'value'),
    State({'type': 'pallet-wid', 'index': ALL}, 'value'), State({'type': 'pallet-wid-unit', 'index': ALL}, 'value'),
    State({'type': 'pallet-hgt', 'index': ALL}, 'value'), State({'type': 'pallet-hgt-unit', 'index': ALL}, 'value'),
    State({'type': 'pallet-wgt', 'index': ALL}, 'value'),
    State({'type': 'pallet-floor', 'index': ALL}, 'value'),
    State({'type': 'pallet-row', 'index': ALL}, 'value'),
    State({'type': 'pallet-rack', 'index': ALL}, 'value'),
    State({'type': 'pallet-type', 'index': ALL}, 'id'),
    prevent_initial_call=True
)
def generate_layout(n_gen, n_clr, is_2d,
                    L, Lu, W, Wu, H, Hu, n_blks, bg, bgu,
                    r_floors, r_rows, r_counts,
                    # NOTE: Argument order MUST match State order above
                    gap_vals, gap_units, gap_ids,       # Rack Gaps
                    gf, gfu, gb, gbu, gl, glu, gr, gru, # Wall Gaps
                    p_types, p_ls, p_lus, p_ws, p_wus, p_hs, p_hus, p_ws_val, p_fs, p_rs, p_racks, p_ids):
    
    if ctx.triggered_id == "btn-clear": return go.Figure()

    block_configs = []
    for i in range(n_blks):
        # Handle Rack Gaps
        block_custom_gaps_cm = []
        for g_idx, g_id_obj in enumerate(gap_ids):
            # Parse ID safely
            try:
                if isinstance(g_id_obj, str): g_id_obj = json.loads(g_id_obj.replace("'", '"'))
                id_idx = str(g_id_obj['index'])
                
                # Check if this gap belongs to current block i
                # ID format: "blockIndex-gapIndex" (e.g. "0-0", "0-1")
                if id_idx.startswith(f"{i}-"):
                    val = float(gap_vals[g_idx] or 0)
                    unit = gap_units[g_idx]
                    block_custom_gaps_cm.append(to_cm(val, unit))
            except Exception as e:
                print(f"Skipping gap {g_idx}: {e}")
                continue

        # Handle Pallets
        block_pallets = []
        for p_idx, p_id_obj in enumerate(p_ids):
            try:
                if isinstance(p_id_obj, str): p_id_obj = json.loads(p_id_obj.replace("'", '"'))
                id_idx = str(p_id_obj['index'])
                
                # Check if pallet belongs to current block i
                # ID format: "blockIndex-palletIndex"
                if id_idx.startswith(f"{i}-"):
                    block_pallets.append({
                        "type": p_types[p_idx],
                        "weight": float(p_ws_val[p_idx] or 0),
                        "length_cm": to_cm(p_ls[p_idx], p_lus[p_idx]),
                        "width_cm": to_cm(p_ws[p_idx], p_wus[p_idx]),
                        "height_cm": to_cm(p_hs[p_idx], p_hus[p_idx]),
                        "position": {
                            "floor": int(p_fs[p_idx]),
                            "row": int(p_rs[p_idx]),
                            "col": int(p_racks[p_idx])
                        }
                    })
            except Exception:
                continue
        
        b_conf = {
            "block_index": i,
            "rack_config": {
                "num_floors": int(r_floors[i]),
                "num_rows": int(r_rows[i]),
                "num_racks": int(r_counts[i]),
                "custom_gaps": block_custom_gaps_cm,
                "gap_front": float(gf[i] or 0),
                "gap_back": float(gb[i] or 0),
                "gap_left": float(gl[i] or 0),
                "gap_right": float(gr[i] or 0),
                "wall_gap_unit": gfu[i]
            },
            "pallet_configs": block_pallets
        }
        block_configs.append(b_conf)

    warehouse_config = {
        "id": "vis-1",
        "warehouse_dimensions": {"length": float(L), "width": float(W), "height": float(H), "unit": Lu},
        "num_blocks": int(n_blks),
        "block_gap": float(bg),
        "block_gap_unit": bgu,
        "block_configs": block_configs
    }

    try:
        response = requests.post(f"{BACKEND_URL}/api/warehouse/create", json=warehouse_config)
        response.raise_for_status()
        layout_data = response.json()["layout"]
    except Exception as e:
        print(f"API Error: {e}")
        return go.Figure()

    fig = go.Figure()
    is_3d = not is_2d
    wh_L, wh_W, wh_H = to_cm(L, Lu), to_cm(W, Wu), to_cm(H, Hu)
    pallet_colors = {'wooden': '#8B4513', 'plastic': '#1E90FF', 'metal': '#A9A9A9'}

    if layout_data and "blocks" in layout_data:
        for block in layout_data["blocks"]:
            b_pos, b_dim = block["position"], block["dimensions"]
            
            # Draw Block
            bx = [b_pos["x"]-b_dim["width"]/2, b_pos["x"]+b_dim["width"]/2, b_pos["x"]+b_dim["width"]/2, b_pos["x"]-b_dim["width"]/2, b_pos["x"]-b_dim["width"]/2]
            by = [0, 0, b_dim["length"], b_dim["length"], 0]
            if is_3d:
                fig.add_trace(go.Scatter3d(x=bx, y=by, z=[0]*5, mode='lines', line=dict(color='blue'), name=block["id"]))
            else:
                fig.add_trace(go.Scatter(x=bx, y=by, mode='lines', line=dict(color='blue', dash='dash'), name=block["id"]))

            for rack in block.get("racks", []):
                r_pos, r_dim = rack["position"], rack["dimensions"]
                # Draw Rack
                if is_3d:
                    fig.add_trace(go.Mesh3d(**create_cube_vertices(r_pos["x"]-r_dim["width"]/2, r_pos["y"]-r_dim["length"]/2, r_pos["z"]-r_dim["height"]/2, r_dim["width"], r_dim["length"], r_dim["height"]), opacity=0.1, color='gray', hoverinfo='skip'))
                elif rack["indices"]["floor"] == 1:
                    rx = [r_pos["x"]-r_dim["width"]/2, r_pos["x"]+r_dim["width"]/2, r_pos["x"]+r_dim["width"]/2, r_pos["x"]-r_dim["width"]/2, r_pos["x"]-r_dim["width"]/2]
                    ry = [r_pos["y"]-r_dim["length"]/2, r_pos["y"]-r_dim["length"]/2, r_pos["y"]+r_dim["length"]/2, r_pos["y"]+r_dim["length"]/2, r_pos["y"]-r_dim["length"]/2]
                    fig.add_trace(go.Scatter(x=rx, y=ry, mode='lines', line=dict(color='gray'), hoverinfo='skip'))
                
                # Draw Pallets
                for p in rack.get("pallets", []):
                    p_dim, col = p["dims"], pallet_colors.get(p["type"], 'brown')
                    if is_3d:
                        pz = r_pos["z"] - r_dim["height"]/2 + p_dim["height"]/2
                        fig.add_trace(go.Mesh3d(**create_cube_vertices(r_pos["x"]-p_dim["width"]/2, r_pos["y"]-p_dim["length"]/2, pz-p_dim["height"]/2, p_dim["width"], p_dim["length"], p_dim["height"]), color=col, opacity=1.0, name=f"Pallet {p['type']}"))
                    else:
                        fig.add_trace(go.Scatter(x=[r_pos["x"]], y=[r_pos["y"]], mode='markers', marker=dict(color=col, size=10), name=f"Pallet {p['type']}"))

    layout_dict = dict(margin=dict(l=0,r=0,t=0,b=0))
    if is_3d:
        layout_dict['scene'] = dict(xaxis=dict(title='Width (cm)', range=[-wh_W/2-100, wh_W/2+100]), yaxis=dict(title='Length (cm)', range=[0, wh_L+100]), zaxis=dict(title='Height (cm)', range=[0, wh_H+100]), aspectmode='data')
    else:
        layout_dict.update(dict(xaxis=dict(title='Width (cm)', range=[-wh_W/2-100, wh_W/2+100]), yaxis=dict(title='Length (cm)', range=[0, wh_L+100])))
        
    fig.update_layout(**layout_dict)
    return fig

if __name__ == "__main__":
    app.run(debug=True, port=8050)