import os
import sys

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from config import Config
from database.db import db, User, Product, Sale, MarketData, PriceRecommendation


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app


def initialize_mysql_database(create_demo_account: bool = True):
    """
    Initializes the MySQL database schema and optionally creates a starter demo user.
    """
    print("\n" + "=" * 65)
    print("   INITIALIZING MYSQL DATABASE: dynamic_price_db")
    print("=" * 65)

    app = create_app()
    with app.app_context():
        print("[1/3] Creating relational tables in MySQL (dynamic_price_db)...")
        db.create_all()
        print("      [+] Table 'users' created / verified.")
        print("      [+] Table 'products' created / verified (with user_id FK).")
        print("      [+] Table 'sales' created / verified (with user_id FK).")
        print("      [+] Table 'market_data' created / verified (with user_id FK).")
        print("      [+] Table 'price_recommendations' created / verified (with user_id FK).")

        if create_demo_account:
            demo_user = User.query.filter_by(username="demo_user").first()
            if not demo_user:
                print("\n[2/3] Creating starter demo user account...")
                demo_user = User(
                    username="demo_user",
                    email="demo@example.com"
                )
                demo_user.set_password("demo123")
                db.session.add(demo_user)
                db.session.commit()
                print("      [+] Demo User created: username='demo_user' | password='demo123'")

                # Seed sample products specifically under demo_user's user_id
                print("\n[3/3] Seeding initial products for demo_user (ID: {})...".format(demo_user.id))
                starter_prods = [
                    {"name": "Wireless Noise-Canceling Headphones", "category": "Electronics", "cost": 45.0, "base": 99.99, "curr": 99.99, "comp": 105.0, "inv": 35, "dem": 3, "sea": 4},
                    {"name": "Smart Fitness Watch", "category": "Electronics", "cost": 30.0, "base": 69.99, "curr": 69.99, "comp": 64.99, "inv": 110, "dem": 2, "sea": 3},
                    {"name": "Ergonomic Office Chair", "category": "Furniture", "cost": 75.0, "base": 179.99, "curr": 179.99, "comp": 185.0, "inv": 25, "dem": 3, "sea": 1},
                    {"name": "RGB Mechanical Gaming Keyboard", "category": "Electronics", "cost": 28.0, "base": 59.99, "curr": 59.99, "comp": 55.0, "inv": 140, "dem": 2, "sea": 4}
                ]
                for sp in starter_prods:
                    p = Product(
                        user_id=demo_user.id,
                        name=sp["name"],
                        category=sp["category"],
                        cost_price=sp["cost"],
                        base_price=sp["base"],
                        current_price=sp["curr"]
                    )
                    db.session.add(p)
                    db.session.flush()

                    m = MarketData(
                        user_id=demo_user.id,
                        product_id=p.id,
                        competitor_price=sp["comp"],
                        demand_level=sp["dem"],
                        inventory_level=sp["inv"],
                        season=sp["sea"]
                    )
                    db.session.add(m)

                db.session.commit()
                print("      [+] Seeded 4 initial products and market records for 'demo_user'.")
            else:
                print("\n[2/3] Demo user account 'demo_user' already exists.")

        print("\n" + "=" * 65)
        print("   DATABASE INITIALIZATION COMPLETE & READY IN MYSQL!")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    initialize_mysql_database(create_demo_account=True)
