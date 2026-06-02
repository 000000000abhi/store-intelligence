import json
from shapely.geometry import Point, Polygon

class ZoneClassifier:
    def __init__(self, layout_file="/data/store_layout.json", store_id="STORE_BLR_002"):
        self.zones = {}
        self.sku_zones = {}
        try:
            with open(layout_file, 'r') as f:
                layout_data = json.load(f)
                
            store_data = layout_data.get(store_id, {})
            zones_data = store_data.get("zones", [])
            
            for z in zones_data:
                zone_id = z["zone_id"]
                poly_coords = z["polygon"]
                if len(poly_coords) >= 3:
                    self.zones[zone_id] = Polygon(poly_coords)
                    self.sku_zones[zone_id] = z.get("sku_zone")
        except FileNotFoundError:
            pass # Suppress warning, we will fallback to filename-based zones
        except Exception as e:
            pass
    def get_zone(self, bbox):
        if not self.zones:
            return None
            
        x1, y1, x2, y2 = bbox
        # Use the bottom-center of the bounding box as the person's 'feet' location
        centroid = Point((x1 + x2) / 2.0, y2)
        
        for zone_id, poly in self.zones.items():
            if poly.contains(centroid):
                return zone_id
                
        return None
        
    def get_sku_zone(self, zone_id):
        return self.sku_zones.get(zone_id)
