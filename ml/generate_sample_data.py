import os
import random
import pandas as pd
import numpy as np

# Set random seed for reproducibility in laboratory testing
np.random.seed(42)
random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

CSV_FILE = os.path.join(DATA_DIR, "sample_data.csv")

PRODUCTS_CATALOG = [
    {"name": "Wireless Noise-Canceling Headphones", "category": "Electronics", "cost_price": 45.0, "base_price": 99.99},
    {"name": "Smart Fitness Watch", "category": "Electronics", "cost_price": 30.0, "base_price": 69.99},
    {"name": "Ergonomic Office Chair", "category": "Furniture", "cost_price": 75.0, "base_price": 179.99},
    {"name": "RGB Mechanical Gaming Keyboard", "category": "Electronics", "cost_price": 28.0, "base_price": 59.99},
    {"name": "Stainless Steel Thermal Water Bottle", "category": "Home & Kitchen", "cost_price": 8.0, "base_price": 24.99},
    {"name": "Organic Cotton Running T-Shirt", "category": "Apparel", "cost_price": 6.5, "base_price": 19.99},
    {"name": "Compact Cold Brew Coffee Maker", "category": "Home & Kitchen", "cost_price": 15.0, "base_price": 39.99},
    {"name": "Ultra-Slim 7-in-1 USB-C Hub", "category": "Accessories", "cost_price": 12.0, "base_price": 34.99},
    {"name": "Adjustable Aluminum Laptop Stand", "category": "Accessories", "cost_price": 11.0, "base_price": 29.99},
    {"name": "Water-Resistant Outdoor Backpack", "category": "Travel", "cost_price": 22.0, "base_price": 54.99}
]

def generate_dataset(num_samples=800):
    rows = []
    
    for i in range(num_samples):
        # Pick a product definition
        prod_idx = i % len(PRODUCTS_CATALOG)
        prod = PRODUCTS_CATALOG[prod_idx]
        
        cost_price = prod["cost_price"]
        base_price = prod["base_price"]
        
        # Current price fluctuates slightly around base_price (-10% to +10%)
        current_price = round(base_price * random.uniform(0.90, 1.10), 2)
        
        # Competitor price fluctuates around base_price (-15% to +15%)
        competitor_price = round(base_price * random.uniform(0.85, 1.15), 2)
        
        # Demand level: 1 (Low), 2 (Medium), 3 (High)
        demand_level = random.choices([1, 2, 3], weights=[0.25, 0.50, 0.25])[0]
        
        # Inventory level: 10 to 300 units
        inventory_level = random.randint(15, 250)
        
        # Season: 1 (Spring), 2 (Summer), 3 (Fall), 4 (Winter)
        season = random.choice([1, 2, 3, 4])
        
        # Demand & Season impact on sales quantity
        # Price sensitivity: higher current_price decreases quantity sold
        price_ratio = current_price / base_price
        base_demand_multiplier = {1: 0.7, 2: 1.0, 3: 1.4}[demand_level]
        season_multiplier = 1.25 if season == 4 else (1.1 if season == 2 else 0.95)
        
        # Quantity sold calculation (Elasticity formula)
        quantity_sold = int(max(3, (40 * base_demand_multiplier * season_multiplier / (price_ratio ** 1.3)) + random.gauss(0, 4)))
        
        # Ground-truth Optimal Selling Price Calculation:
        # 1. Start with competitor anchor (40% weight) + base price anchor (60% weight)
        target_price = (competitor_price * 0.40) + (base_price * 0.60)
        
        # 2. Demand adjustments:
        # High demand (+6% to +12%), Low demand (-5% to -10%)
        if demand_level == 3:
            target_price *= random.uniform(1.05, 1.10)
        elif demand_level == 1:
            target_price *= random.uniform(0.92, 0.96)
            
        # 3. Inventory scarcity adjustment:
        # Low inventory (< 40 units) -> scarcity pricing power (+5%)
        # High inventory (> 180 units) -> clearance markdown (-6%)
        if inventory_level < 40:
            target_price *= 1.05
        elif inventory_level > 180:
            target_price *= 0.94
            
        # 4. Seasonal adjustment:
        if season == 4:  # Holiday/Winter peak
            target_price *= 1.06
            
        # 5. Guardrail: Must never drop below cost_price + 15% profit margin
        min_allowed_price = cost_price * 1.15
        target_price = max(target_price, min_allowed_price)
        
        optimal_selling_price = round(target_price, 2)
        
        rows.append({
            "product_id": prod_idx + 1,
            "product_name": prod["name"],
            "category": prod["category"],
            "cost_price": cost_price,
            "base_price": base_price,
            "current_price": current_price,
            "competitor_price": competitor_price,
            "demand_level": demand_level,
            "inventory_level": inventory_level,
            "season": season,
            "quantity_sold": quantity_sold,
            "optimal_selling_price": optimal_selling_price
        })
        
    df = pd.DataFrame(rows)
    df.to_csv(CSV_FILE, index=False)
    print(f"[DATASET] Generated {len(df)} sample records successfully -> {CSV_FILE}")
    return df

if __name__ == "__main__":
    generate_dataset()
