from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize SQLAlchemy instance
db = SQLAlchemy()


class User(db.Model):
    """
    User Model
    Stores authenticated user credentials and profile information.
    Enforces multi-tenant data isolation across all business records.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 1:N Relationships - Cascades automatically if a user account is deleted
    products = db.relationship('Product', backref='owner', cascade='all, delete-orphan', lazy=True)
    sales = db.relationship('Sale', backref='owner', cascade='all, delete-orphan', lazy=True)
    market_records = db.relationship('MarketData', backref='owner', cascade='all, delete-orphan', lazy=True)
    recommendations = db.relationship('PriceRecommendation', backref='owner', cascade='all, delete-orphan', lazy=True)

    def set_password(self, password: str):
        """Hashes password using secure PBKDF2/scrypt before storage."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifies given password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""
        }


class Product(db.Model):
    """
    Product Model
    Represents an item sold in a user's catalog.
    Scoped strictly by user_id.
    """
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="General")
    cost_price = db.Column(db.Float, nullable=False)       # Procurement / Production unit cost floor
    base_price = db.Column(db.Float, nullable=False)       # Standard MSRP / Catalog baseline
    current_price = db.Column(db.Float, nullable=False)    # Currently active dynamic selling price
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships to child records
    sales = db.relationship('Sale', backref='product', cascade='all, delete-orphan', lazy=True)
    market_data = db.relationship('MarketData', backref='product', cascade='all, delete-orphan', lazy=True)
    recommendations = db.relationship('PriceRecommendation', backref='product', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "category": self.category,
            "cost_price": round(self.cost_price, 2),
            "base_price": round(self.base_price, 2),
            "current_price": round(self.current_price, 2),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""
        }


class Sale(db.Model):
    """
    Sale Model
    Stores historical sales transactions entered by the user.
    Scoped strictly by user_id and product_id.
    """
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    quantity_sold = db.Column(db.Integer, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    total_revenue = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.Date, nullable=False, default=date.today)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else "N/A",
            "quantity_sold": self.quantity_sold,
            "selling_price": round(self.selling_price, 2),
            "total_revenue": round(self.total_revenue, 2),
            "sale_date": self.sale_date.strftime("%Y-%m-%d") if self.sale_date else ""
        }


class MarketData(db.Model):
    """
    Market Data Model
    Captures competitor prices, demand signals, and warehouse inventory levels for a product.
    Scoped strictly by user_id and product_id.
    """
    __tablename__ = 'market_data'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    competitor_price = db.Column(db.Float, nullable=False)
    demand_level = db.Column(db.Integer, nullable=False)     # 1: Low, 2: Medium, 3: High
    inventory_level = db.Column(db.Integer, nullable=False)  # Current available units
    season = db.Column(db.Integer, nullable=False)           # 1: Spring, 2: Summer, 3: Fall, 4: Winter
    recorded_date = db.Column(db.Date, nullable=False, default=date.today)

    @property
    def demand_label(self):
        labels = {1: "Low", 2: "Medium", 3: "High"}
        return labels.get(self.demand_level, "Unknown")

    @property
    def season_label(self):
        labels = {1: "Spring", 2: "Summer", 3: "Fall", 4: "Winter"}
        return labels.get(self.season, "Unknown")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else "N/A",
            "competitor_price": round(self.competitor_price, 2),
            "demand_level": self.demand_level,
            "demand_label": self.demand_label,
            "inventory_level": self.inventory_level,
            "season": self.season,
            "season_label": self.season_label,
            "recorded_date": self.recorded_date.strftime("%Y-%m-%d") if self.recorded_date else ""
        }


class PriceRecommendation(db.Model):
    """
    Price Recommendation Model
    Stores AI-generated price suggestions, variance from current price, and applied status.
    Scoped strictly by user_id and product_id.
    """
    __tablename__ = 'price_recommendations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    current_price = db.Column(db.Float, nullable=False)
    recommended_price = db.Column(db.Float, nullable=False)
    price_difference = db.Column(db.Float, nullable=False)   # recommended_price - current_price
    confidence_score = db.Column(db.Float, default=0.88)
    reason = db.Column(db.String(255), nullable=True)        # Explainable AI rationale
    status = db.Column(db.String(20), default="Pending")     # 'Pending' or 'Applied'
    generated_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else "N/A",
            "current_price": round(self.current_price, 2),
            "recommended_price": round(self.recommended_price, 2),
            "price_difference": round(self.price_difference, 2),
            "confidence_score": round(self.confidence_score * 100, 1),
            "reason": self.reason or "Model recommendation",
            "status": self.status,
            "generated_at": self.generated_at.strftime("%Y-%m-%d %H:%M") if self.generated_at else ""
        }
