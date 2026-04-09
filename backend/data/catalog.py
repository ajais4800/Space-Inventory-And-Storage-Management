import json
from datetime import date, timedelta
import random

PERISHABLES_CATALOG = [
    {
        "sku": "BAN001", "name": "Banana", "category": "tropical_fruit",
        "unit": "kg", "reorder_point_kg": 200, "lead_days": 2,
        "storage_temp_min_c": 13, "storage_temp_max_c": 15,
        "shelf_life_days": 7, "ripeness_curve": "sigmoid",
        "ripeness_peak_day": 4, "varieties": ["Cavendish", "Robusta", "Red Banana"],
        "zone": "ambient"
    },
    {
        "sku": "AVG001", "name": "Avocado", "category": "tropical_fruit",
        "unit": "kg", "reorder_point_kg": 100, "lead_days": 3,
        "storage_temp_min_c": 5, "storage_temp_max_c": 13,
        "shelf_life_days": 10, "ripeness_curve": "sigmoid",
        "ripeness_peak_day": 6, "varieties": ["Hass", "Fuerte", "Bacon"],
        "zone": "refrigerated"
    },
    {
        "sku": "MNG001", "name": "Mango", "category": "tropical_fruit",
        "unit": "kg", "reorder_point_kg": 150, "lead_days": 2,
        "storage_temp_min_c": 10, "storage_temp_max_c": 15,
        "shelf_life_days": 8, "ripeness_curve": "sigmoid",
        "ripeness_peak_day": 5, "varieties": ["Alphonso", "Kesar", "Dasheri", "Totapuri"],
        "zone": "ambient"
    },
    {
        "sku": "TOM001", "name": "Tomato", "category": "vegetable",
        "unit": "kg", "reorder_point_kg": 300, "lead_days": 1,
        "storage_temp_min_c": 13, "storage_temp_max_c": 21,
        "shelf_life_days": 7, "ripeness_curve": "linear",
        "ripeness_peak_day": 3, "varieties": ["Roma", "Cherry", "Beefsteak"],
        "zone": "ambient"
    },
    {
        "sku": "STR001", "name": "Strawberry", "category": "berry",
        "unit": "kg", "reorder_point_kg": 80, "lead_days": 1,
        "storage_temp_min_c": 0, "storage_temp_max_c": 4,
        "shelf_life_days": 5, "ripeness_curve": "fast_sigmoid",
        "ripeness_peak_day": 2, "varieties": ["Chandler", "Albion"],
        "zone": "refrigerated"
    },
    {
        "sku": "LET001", "name": "Lettuce", "category": "leafy_green",
        "unit": "kg", "reorder_point_kg": 120, "lead_days": 1,
        "storage_temp_min_c": 0, "storage_temp_max_c": 4,
        "shelf_life_days": 7, "ripeness_curve": "linear",
        "ripeness_peak_day": 1, "varieties": ["Romaine", "Iceberg", "Butterhead"],
        "zone": "refrigerated"
    },
    {
        "sku": "MLK001", "name": "Milk", "category": "dairy",
        "unit": "liters", "reorder_point_kg": 500, "lead_days": 1,
        "storage_temp_min_c": 2, "storage_temp_max_c": 4,
        "shelf_life_days": 7, "ripeness_curve": "linear",
        "ripeness_peak_day": 1, "varieties": ["Full Fat", "Skimmed", "Semi-Skimmed"],
        "zone": "cold_chain"
    },
    {
        "sku": "CHE001", "name": "Cheese", "category": "dairy",
        "unit": "kg", "reorder_point_kg": 60, "lead_days": 2,
        "storage_temp_min_c": 2, "storage_temp_max_c": 8,
        "shelf_life_days": 30, "ripeness_curve": "flat",
        "ripeness_peak_day": 1, "varieties": ["Cheddar", "Mozzarella", "Gouda"],
        "zone": "refrigerated"
    },
    {
        "sku": "FSH001", "name": "Salmon", "category": "seafood",
        "unit": "kg", "reorder_point_kg": 100, "lead_days": 1,
        "storage_temp_min_c": 0, "storage_temp_max_c": 2,
        "shelf_life_days": 3, "ripeness_curve": "fast_sigmoid",
        "ripeness_peak_day": 1, "varieties": ["Atlantic", "Pacific"],
        "zone": "cold_chain"
    },
    {
        "sku": "CHK001", "name": "Chicken", "category": "poultry",
        "unit": "kg", "reorder_point_kg": 200, "lead_days": 1,
        "storage_temp_min_c": 0, "storage_temp_max_c": 4,
        "shelf_life_days": 3, "ripeness_curve": "fast_sigmoid",
        "ripeness_peak_day": 1, "varieties": ["Whole", "Breast", "Thigh"],
        "zone": "cold_chain"
    },
    {
        "sku": "APL001", "name": "Apple", "category": "temperate_fruit",
        "unit": "kg", "reorder_point_kg": 250, "lead_days": 3,
        "storage_temp_min_c": 1, "storage_temp_max_c": 4,
        "shelf_life_days": 30, "ripeness_curve": "slow_sigmoid",
        "ripeness_peak_day": 7, "varieties": ["Fuji", "Gala", "Granny Smith", "Honeycrisp"],
        "zone": "refrigerated"
    },
    {
        "sku": "ORG001", "name": "Orange", "category": "citrus",
        "unit": "kg", "reorder_point_kg": 200, "lead_days": 2,
        "storage_temp_min_c": 3, "storage_temp_max_c": 9,
        "shelf_life_days": 14, "ripeness_curve": "slow_sigmoid",
        "ripeness_peak_day": 5, "varieties": ["Navel", "Valencia", "Blood"],
        "zone": "refrigerated"
    },
    {
        "sku": "GRP001", "name": "Grapes", "category": "berry",
        "unit": "kg", "reorder_point_kg": 100, "lead_days": 2,
        "storage_temp_min_c": 0, "storage_temp_max_c": 2,
        "shelf_life_days": 14, "ripeness_curve": "sigmoid",
        "ripeness_peak_day": 4, "varieties": ["Red Globe", "Thompson Seedless", "Black Muscat"],
        "zone": "refrigerated"
    },
    {
        "sku": "SPN001", "name": "Spinach", "category": "leafy_green",
        "unit": "kg", "reorder_point_kg": 80, "lead_days": 1,
        "storage_temp_min_c": 0, "storage_temp_max_c": 4,
        "shelf_life_days": 5, "ripeness_curve": "fast_sigmoid",
        "ripeness_peak_day": 1, "varieties": ["Baby", "Mature"],
        "zone": "refrigerated"
    },
    {
        "sku": "BRO001", "name": "Broccoli", "category": "vegetable",
        "unit": "kg", "reorder_point_kg": 100, "lead_days": 2,
        "storage_temp_min_c": 0, "storage_temp_max_c": 4,
        "shelf_life_days": 7, "ripeness_curve": "linear",
        "ripeness_peak_day": 2, "varieties": ["Standard", "Broccolini"],
        "zone": "refrigerated"
    }
]

STORAGE_CONTAINERS = [
    {"container_id": "CNT-A", "name": "Ambient Zone A", "zone_type": "ambient", "capacity_kg": 2000, "rows": 5, "cols": 4, "depths": 3, "temp_c": 18},
    {"container_id": "CNT-B", "name": "Ambient Zone B", "zone_type": "ambient", "capacity_kg": 1500, "rows": 4, "cols": 4, "depths": 3, "temp_c": 16},
    {"container_id": "REF-A", "name": "Refrigerated Zone A", "zone_type": "refrigerated", "capacity_kg": 1000, "rows": 4, "cols": 3, "depths": 3, "temp_c": 3},
    {"container_id": "REF-B", "name": "Refrigerated Zone B", "zone_type": "refrigerated", "capacity_kg": 800, "rows": 3, "cols": 3, "depths": 3, "temp_c": 5},
    {"container_id": "REF-C", "name": "Refrigerated Zone C", "zone_type": "refrigerated", "capacity_kg": 600, "rows": 3, "cols": 3, "depths": 2, "temp_c": 7},
    {"container_id": "CC-A", "name": "Cold Chain Zone A", "zone_type": "cold_chain", "capacity_kg": 500, "rows": 3, "cols": 3, "depths": 2, "temp_c": 1},
    {"container_id": "CC-B", "name": "Cold Chain Zone B", "zone_type": "cold_chain", "capacity_kg": 400, "rows": 2, "cols": 3, "depths": 2, "temp_c": 2},
    {"container_id": "FRZ-A", "name": "Freezer Zone A", "zone_type": "freezer", "capacity_kg": 300, "rows": 2, "cols": 3, "depths": 2, "temp_c": -18}
]

CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Surat"]

CLIENT_NAMES = [
    "FreshMart Superstore", "QuickBite Restaurants", "GreenLeaf Organics", "CityGrocers Chain",
    "Hotel Grand Palace", "StarChef Catering", "FoodHub Express", "NatureBasket Retail",
    "CoolFresh Distributors", "Urban Eats Co.", "SpiceRoute Hotels", "PeakFresh Markets",
    "BlueStar Catering", "GoldenHarvest Stores", "SunRise Groceries", "FarmToFork Delivery",
    "CrispFresh Markets", "EasyEats Restaurants", "ProFresh Suppliers", "VitaFoods Chain",
    "Harvest Moon Organics", "CityPlate Catering", "PrimeFresh Co.", "GreenBox Delivery",
    "AquaFresh Seafood", "TopChef Supplies", "FreshFusion Markets", "EcoFarm Organics",
    "CloudKitchen Hub", "MegaFresh Wholesale", "TasteFirst Catering", "NutriStore Chain",
    "LocalHarvest Co.", "SwiftFresh Logistics", "DailyFresh Outlets", "GrainBowl Restaurants",
    "ColdChain Express", "FarmFresh Direct", "VeggieWorld Markets", "FreshPath Distributors",
    "SilkRoute Catering", "PureHarvest Stores", "ZeroWaste Grocers", "BrightFresh Co.",
    "ChillBox Logistics", "GardenGate Organic", "CityFarm Markets", "QuickFresh Delivery",
    "AlphaFresh Wholesale", "OmegaSupplies Chain"
]
