# backend/warehouse_calc.py (UPDATED VERSION)
import math

class WarehouseCalculator:
    def __init__(self):
        # Base unit is now Centimeters (cm)
        self.conversion_factors = {
            'cm': 1.0, 
            'm': 100.0, 
            'km': 100000.0,
            'in': 2.54, 
            'ft': 30.48, 
            'yd': 91.44, 
            'mi': 160934.4
        }
    
    def convert_to_centimeters(self, value, unit):
        if unit not in self.conversion_factors:
            raise ValueError(f"Unsupported unit: {unit}")
        return value * self.conversion_factors[unit]
    
    def create_warehouse_layout(self, config):
        # 1. Warehouse Dimensions
        wh_dims = config['warehouse_dimensions']
        wh_length = self.convert_to_centimeters(wh_dims['length'], wh_dims['unit'])
        wh_width = self.convert_to_centimeters(wh_dims['width'], wh_dims['unit'])
        wh_height = self.convert_to_centimeters(wh_dims['height'], wh_dims['unit'])
        
        num_blocks = config['num_blocks']
        block_gap = self.convert_to_centimeters(config['block_gap'], config['block_gap_unit'])
        
        # 2. Calculate Block Sizes
        total_gap_width = block_gap * (num_blocks - 1) if num_blocks > 1 else 0
        available_width = wh_width - total_gap_width
        
        if available_width <= 0: available_width = 100.0 # Safety fallback
        
        block_width = available_width / num_blocks
        block_length = wh_length 
        
        blocks_layout = []
        
        total_occupied_width = (block_width * num_blocks) + total_gap_width
        start_x = -total_occupied_width / 2 + block_width / 2
        
        # 3. Generate Each Block
        for i, block_conf in enumerate(config['block_configs']):
            block_id = f"block_{i + 1}"
            x_offset = start_x + i * (block_width + block_gap)
            
            block_data = {
                'id': block_id,
                'name': f"Block {i + 1}",
                'position': {'x': x_offset, 'y': 0, 'z': 0},
                'dimensions': {
                    'width': block_width,
                    'length': block_length,
                    'height': wh_height
                },
                'color': self.get_block_color(i),
                'racks': []
            }
            
            # 4. Generate Racks
            racks = self.calculate_racks_for_block(block_data['dimensions'], block_conf)
            block_data['racks'] = racks
            
            blocks_layout.append(block_data)
            
        return {
            'warehouse_dimensions': config['warehouse_dimensions'],
            'blocks': blocks_layout,
            'total_pallets': sum(len(block_conf.get('pallet_configs', [])) for block_conf in config['block_configs'])
        }

    def calculate_racks_for_block(self, block_dims, block_conf):
        racks = []
        rack_cfg = block_conf['rack_config']
        
        # Wall gaps
        gap_f = self.convert_to_centimeters(rack_cfg['gap_front'], rack_cfg['wall_gap_unit'])
        gap_b = self.convert_to_centimeters(rack_cfg['gap_back'], rack_cfg['wall_gap_unit'])
        gap_l = self.convert_to_centimeters(rack_cfg['gap_left'], rack_cfg['wall_gap_unit'])
        gap_r = self.convert_to_centimeters(rack_cfg['gap_right'], rack_cfg['wall_gap_unit'])
        
        # Custom Rack Gaps
        custom_gaps = [self.convert_to_centimeters(g, rack_cfg['gap_unit']) for g in rack_cfg.get('custom_gaps', [])]
        
        num_rows = rack_cfg['num_rows']
        num_racks_total = rack_cfg['num_racks']
        num_floors = rack_cfg['num_floors']
        
        racks_per_row = math.ceil(num_racks_total / num_rows) if num_rows > 0 else 0
        if racks_per_row == 0: return []
        
        # Determine maximum total gap width in any single row
        max_row_gap_sum = 0
        for r in range(num_rows):
            current_row_gap_sum = 0
            start_rack_idx = r * racks_per_row
            for c in range(racks_per_row - 1):
                gap_idx = start_rack_idx + c
                if gap_idx < len(custom_gaps):
                    current_row_gap_sum += custom_gaps[gap_idx]
            if current_row_gap_sum > max_row_gap_sum:
                max_row_gap_sum = current_row_gap_sum

        # Calculate Rack Dimensions
        avail_w = block_dims['width'] - gap_l - gap_r
        avail_l = block_dims['length'] - gap_f - gap_b
        
        rack_w = (avail_w - max_row_gap_sum) / racks_per_row
        if rack_w < 10.0: rack_w = 50.0 # Safety fallback (50cm)
        
        row_gap_std = 150.0 # 150cm aisle
        total_row_gaps = row_gap_std * (num_rows - 1) if num_rows > 1 else 0
        rack_l = (avail_l - total_row_gaps) / num_rows
        
        rack_h = block_dims['height'] * 0.8
        floor_h = rack_h / num_floors
        
        global_rack_count = 0
        
        for r in range(num_rows):
            current_x_offset = -block_dims['width']/2 + gap_l
            
            for c in range(racks_per_row):
                if global_rack_count >= num_racks_total: break
                
                gap_before = 0
                if c > 0:
                    gap_idx = global_rack_count - 1
                    if gap_idx < len(custom_gaps):
                        gap_before = custom_gaps[gap_idx]
                
                current_x_offset += gap_before
                
                x_pos = current_x_offset + (rack_w / 2)
                z_start = -block_dims['length']/2 + gap_f + (rack_l/2)
                z_pos = z_start + r * (rack_l + row_gap_std)
                
                rack_id = f"rack_{r+1}_{c+1}"
                
                for f in range(num_floors):
                    y_pos = (f * floor_h) + (floor_h/2)
                    
                    rack_data = {
                        'id': f"{rack_id}_f{f+1}",
                        'position': {'x': x_pos, 'y': y_pos, 'z': z_pos},
                        'dimensions': {
                            'width': rack_w,
                            'length': rack_l,
                            'height': floor_h
                        },
                        'floor': f+1, 'row': r+1, 'column': c+1,
                        'pallets': []  # List to hold pallets in this rack position
                    }
                    
                    # Check for pallets in this position
                    pallet_configs = block_conf.get('pallet_configs', [])
                    for pallet_conf in pallet_configs:
                        pallet_pos = pallet_conf.get('position', {})
                        if (pallet_pos.get('floor') == f+1 and 
                            pallet_pos.get('row') == r+1 and 
                            pallet_pos.get('col') == c+1):
                            rack_data['pallets'].append(self.create_pallet_data(pallet_conf))
                    
                    racks.append(rack_data)
                
                current_x_offset += rack_w
                global_rack_count += 1
                
        return racks

    def create_pallet_data(self, pallet_conf):
        return {
            'type': pallet_conf['type'],
            'color': pallet_conf.get('color', '#8B4513'),
            'weight': pallet_conf['weight'],
            'dimensions': {
                'length': self.convert_to_centimeters(pallet_conf['length'], pallet_conf.get('unit', 'cm')),
                'width': self.convert_to_centimeters(pallet_conf['width'], pallet_conf.get('unit', 'cm')),
                'height': self.convert_to_centimeters(pallet_conf['height'], pallet_conf.get('unit', 'cm')),
            },
            'position': pallet_conf['position']
        }

    def get_block_color(self, index):
        colors = ['#FF6B6B', '#4ECDC4', '#FFD166', '#06D6A0', '#118AB2', '#073B4C', '#7209B7', '#F72585']
        return colors[index % len(colors)]