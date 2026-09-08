import os
import sys
from datetime import datetime, date, timedelta
import random

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from config import Config
from database.db import db, Product, Sale, MarketData, PriceRecommendation

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app

def seed_database():
    app = create_app()
    with app.app_context():
        print("[DATABASE] Creating database tables if they do not exist...")
        db.create_all()
        
        # Check if already seeded
        if Product.query.count() > 0:
            print(f"[DATABASE] Database already contains {Product.query.count()} products. Skipping seed.")
            return

        print("[DATABASE] Seeding initial products, sales, and market data...")
        
        initial_products = [
            {"name": "Wireless Noise-Canceling Headphones", "category": "Electronics", "cost_price": 45.0, "base_price": 99.99, "current_price": 99.99},
            {"name": "Smart Fitness Watch", "category": "Electronics", "cost_price": 30.0, "base_price": 69.99, "current_price": 69.99},
            {"name": "Ergonomic Office Chair", "category": "Furniture", "cost_price": 75.0, "base_price": 179.99, "current_price": 179.99},
            {"name": "RGB Mechanical Gaming Keyboard", "category": "Electronics", "cost_price": 28.0, "base_price": 59.99, "current_price": 59.99},
            {"name": "Stainless Steel Thermal Water Bottle", "category": "Home & Kitchen", "cost_price": 8.0, "base_price": 24.99, "current_price": 24.99},
            {"name": "Organic Cotton Running T-Shirt", "category": "Apparel", "cost_price": 6.5, "base_price": 19.99, "current_price": 19.99},
            {"name": "Compact Cold Brew Coffee Maker", "category": "Home & Kitchen", "cost_price": 15.0, "base_price": 39.99, "current_price": 39.99},
            {"name": "Ultra-Slim 7-in-1 USB-C Hub", "category": "Accessories", "cost_price": 12.0, "base_price": 34.99, "current_price": 34.99},
            {"name": "Adjustable Aluminum Laptop Stand", "category": "Accessories", "cost_price": 11.0, "base_price": 29.99, "current_price": 29.99},
            {"name": "Water-Resistant Outdoor Backpack", "category": "Travel", "cost_price": 22.0, "base_price": 54.99, "current_price": 54.99}
        ]

        product_objects = []
        for p in initial_products:
            prod = Product(
                name=p["name"],
                category=p["category"],
                cost_price=p["cost_price"],
                base_price=p["base_price"],
                current_price=p["current_price"]
            )
            db.session.add(prod)
            product_objects.append(prod)
        db.session.commit()
        print(f"  [+] Inserted {len(product_objects)} products.")

        # Seed Market Data for each product
        market_records = []
        today = date.today()
        
        # Realistic settings for each product
        market_configs = [
            {"comp_price": 105.00, "demand": 3, "inventory": 35, "season": 4, "rec_price": 108.50, "reason": "High demand and low inventory (<40) justify +8.5% price increase."},
            {"comp_price": 64.99, "demand": 2, "inventory": 110, "season": 3, "rec_price": 66.50, "reason": "Competitor dropped price; slight adjustment recommended."},
            {"comp_price": 185.00, "demand": 3, "inventory": 25, "season": 1, "rec_price": 184.99, "reason": "High demand office furniture with low stock availability."},
            {"comp_price": 55.00, "demand": 2, "inventory": 140, "season": 4, "rec_price": 57.50, "reason": "Competitor undercutting; match close to market equilibrium."},
            {"comp_price": 26.50, "demand": 2, "inventory": 95, "season": 2, "rec_price": 25.99, "reason": "Stable demand and healthy inventory level."},
            {"comp_price": 18.00, "demand": 1, "inventory": 210, "season": 4, "rec_price": 17.99, "reason": "High stock (>200) and low off-season demand suggest clearance promo."},
            {"comp_price": 42.00, "demand": 3, "inventory": 40, "season": 2, "rec_price": 41.50, "reason": "Summer peak demand for cold brew maker allows premium pricing."},
            {"comp_price": 36.99, "demand": 2, "inventory": 80, "season": 3, "rec_price": 35.99, "reason": "Competitor priced slightly higher; room for profitable margin."},
            {"comp_price": 28.50, "demand": 2, "inventory": 65, "season": 1, "rec_price": 29.50, "reason": "Balanced stock and steady demand curve."},
            {"comp_price": 59.99, "demand": 3, "inventory": 30, "season": 2, "rec_price": 58.00, "reason": "Summer travel season spike and low supply create pricing power."}
        ]

        for i, prod in enumerate(product_objects):
            cfg = market_configs[i]
            m = MarketData(
                product_id=prod.id,
                competitor_price=cfg["comp_price"],
                demand_level=cfg["demand"],
                inventory_level=cfg["inventory"],
                season=cfg["season"],
                recorded_date=today
            )
            db.session.add(m)
            market_records.append(m)
            
            # Initial recommendation entry
            rec = PriceRecommendation(
                product_id=prod.id,
                current_price=prod.current_price,
                recommended_price=cfg["rec_price"],
                price_difference=round(cfg["rec_price"] - prod.current_price, 2),
                confidence_score=0.91,
                reason=cfg["reason"],
                status="Pending"
            )
            db.session.add(rec)
        db.session.commit()
        print(f"  [+] Inserted {len(market_records)} market data records and initial recommendations.")

        # Seed 60 historical sales records
        sales_count = 0
        for prod in product_objects:
            # Generate sales across the past 30 days
            for day_offset in range(1, 28, 4):
                sale_d = today - timedelta(days=day_offset)
                qty = random.randint(4, 25)
                # Historical selling price
                price = round(prod.base_price * random.uniform(0.95, 1.05), 2)
                revenue = round(qty * price, 2)
                sale = Sale(
                    product_id=prod.id,
                    quantity_sold=qty,
                    selling_price=price,
                    total_revenue=revenue,
                    sale_date=sale_d
                )
                db.session.add(sale)
                sales_count += 1
                
        db.session.commit()
        print(f"  [+] Inserted {sales_count} historical sales records.")
        print("[DATABASE] Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
