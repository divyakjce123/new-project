# backend/warehouse_calc.py
import math

class WarehouseCalculator:
    def __init__(self):
        self.conversion_factors = {
            'cm': 1.0, 'm': 100.0, 'km': 100000.0,
            'in': 2.54, 'ft': 30.48, 'yd': 91.44, 'mm': 0.1
        }
    
    def to_cm(self, value, unit):
        """Converts a value from a given unit to centimeters."""
        if value is None: return 0.0
        try:
            val = float(value)
        except ValueError:
            return 0.0
        return val * self.conversion_factors.get(unit.lower(), 1.0)
    
    def create_warehouse_layout(self, config):
        """
        Calculates the physical layout of the warehouse based on the configuration.
        Returns a JSON-serializable dictionary representing the 3D layout.
        """
        wh_dim = config['warehouse_dimensions']
        # Convert warehouse dimensions to cm
        L = self.to_cm(wh_dim['length'], wh_dim['unit'])
        W = self.to_cm(wh_dim['width'], wh_dim['unit'])
        H = self.to_cm(wh_dim['height'], wh_dim['unit'])
        
        n_blocks = config['num_blocks']
        # Convert block gap to cm
        bg = self.to_cm(config['block_gap'], config['block_gap_unit'])
        
        # 1. Calculate Block Size and Starting Position
        total_gaps = bg * (n_blocks - 1) if n_blocks > 1 else 0
        block_w = (W - total_gaps) / n_blocks if n_blocks > 0 else 0
        # Start x is the center of the first block
        start_x = -W/2 + block_w/2
        
        blocks_data = []
        
        # Iterate through each block configuration
        for i, b_conf in enumerate(config['block_configs']):
            # Calculate the center x-coordinate of the current block
            block_x = start_x + i * (block_w + bg)
            
            # 2. Process Wall Gaps (convert to cm)
            rc = b_conf['rack_config']
            gf = self.to_cm(rc['gap_front'], rc['wall_gap_unit'])
            gb = self.to_cm(rc['gap_back'], rc['wall_gap_unit'])
            gl = self.to_cm(rc['gap_left'], rc['wall_gap_unit'])
            gr = self.to_cm(rc['gap_right'], rc['wall_gap_unit'])
            
            # Calculate available space inside the block for racks
            avail_w = block_w - gl - gr
            avail_l = L - gf - gb
            
            rows = rc['num_rows']
            floors = rc['num_floors']
            num_racks = rc['num_racks']
            
            # Calculate how many racks fit per row
            racks_per_row = (num_racks + rows - 1) // rows if rows > 0 else 0
            
            # 3. Process Rack Gaps
            # custom_gaps is already expected to be in cm from the API payload
            custom_gaps = [float(g) for g in rc.get('custom_gaps', [])]
            
            # Determine rack dimensions
            # Sum of gaps in a single row to subtract from available width
            row_gap_sum = sum(custom_gaps[:racks_per_row-1]) if custom_gaps and racks_per_row > 0 else 0
            
            rack_w = (avail_w - row_gap_sum) / racks_per_row if racks_per_row > 0 else 0
            rack_l = avail_l / rows if rows > 0 else 0
            floor_h = H / floors if floors > 0 else 0
            
            racks_data = []
            rack_count = 0
            
            # Generate Racks
            for r in range(rows):
                # Starting x-position for the row (left side + half rack width)
                cx = block_x - block_w/2 + gl + rack_w/2
                # y-position is the center of the rack along the length
                cy = gf + r * rack_l + rack_l/2
                
                for c in range(racks_per_row):
                    if rack_count >= num_racks: break
                    
                    if c > 0:
                        # Add the gap between the previous rack and this one
                        gap_val = custom_gaps[c-1] if (c-1) < len(custom_gaps) else 0
                        cx += gap_val
                    
                    # Create floors for the current rack
                    for f in range(floors):
                        # z-position is the center of the floor height
                        cz = f * floor_h + floor_h/2
                        
                        rack_entry = {
                            "id": f"rack-{i}-{r}-{c}-{f}",
                            # Position is the center of the rack floor cuboid
                            "position": {"x": cx, "y": cy, "z": cz},
                            "dimensions": {"length": rack_l, "width": rack_w, "height": floor_h},
                            "indices": {"floor": f+1, "row": r+1, "col": c+1}
                        }
                        
                        # 4. Check for Pallets placed on this floor
                        for p in b_conf.get('pallet_configs', []):
                            pos = p['position']
                            # User input is 1-based, match with current indices
                            if pos['floor'] == f+1 and pos['row'] == r+1 and pos['col'] == c+1:
                                # Pallet dimensions are already expected in cm from API payload
                                rack_entry.setdefault('pallets', []).append({
                                    "type": p['type'],
                                    "color": p.get('color', '#8B4513'),
                                    # Store full dimensions in cm
                                    "dims": {
                                        "length": p.get('length_cm', 0),
                                        "width": p.get('width_cm', 0),
                                        "height": p.get('height_cm', 0)
                                    }
                                })
                        
                        racks_data.append(rack_entry)
                        
                    # Move center x-position for the next rack in the row
                    cx += rack_w
                    rack_count += 1
            
            # Add block data with its racks
            blocks_data.append({
                "id": f"block_{i+1}",
                # Position is the center of the block cuboid
                "position": {"x": block_x, "y": L/2, "z": H/2},
                "dimensions": {"width": block_w, "length": L, "height": H},
                "racks": racks_data
            })
            
        return {"blocks": blocks_data}