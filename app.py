import os
import json
from functools import wraps
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify
)
from config import Config
from database.db import (
    db, User, Product, Sale, MarketData, PriceRecommendation
)
from ml.predict_price import predict_optimal_price

app = Flask(__name__)
app.config.from_object(Config)
# Initialize database with app
db.init_app(app)

# Ensure tables exist in MySQL on startup
with app.app_context():
    db.create_all()


# -------------------------------------------------------------
# AUTHENTICATION & SECURITY HELPERS
# -------------------------------------------------------------
def login_required(f):
    """
    Decorator to protect routes from unauthenticated access.
    Redirects to /login if user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Returns the current logged-in User instance or None."""
    user_id = session.get("user_id")
    if user_id:
        return db.session.get(User, user_id)
    return None


def get_model_metrics():
    """Reads saved baseline model training metrics if available."""
    metrics_path = os.path.join(os.path.dirname(__file__), "models", "metrics.json")
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None


# -------------------------------------------------------------
# AUTHENTICATION MODULE (REGISTER, LOGIN, LOGOUT)
# -------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """User Registration Route."""
    if session.get("user_id"):
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        # Check existing user
        if User.query.filter_by(username=username).first():
            flash("Username is already taken. Please choose another.", "danger")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("register.html")

        # Create user with hashed password
        try:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            # Automatic login upon registration
            session["user_id"] = new_user.id
            session["username"] = new_user.username
            flash(f"Welcome, {username}! Your account was created successfully.", "success")
            return redirect(url_for("index"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating account: {str(e)}", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """User Login Route."""
    if session.get("user_id"):
        return redirect(url_for("index"))

    if request.method == "POST":
        login_id = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Allow logging in with either username or email
        user = User.query.filter(
            (User.username == login_id) | (User.email == login_id.lower())
        ).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"Signed in successfully as {user.username}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username/email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logs the user out and clears session."""
    username = session.get("username", "User")
    session.clear()
    flash(f"Goodbye {username}! You have been signed out.", "info")
    return redirect(url_for("login"))


# -------------------------------------------------------------
# MODULE 1: USER DASHBOARD
# -------------------------------------------------------------
@app.route("/")
@login_required
def index():
    """
    Executive Dashboard - Scoped strictly to the logged-in user.
    Displays user-specific KPIs, real sales transactions, and recommendations.
    """
    uid = session["user_id"]
    products = Product.query.filter_by(user_id=uid).all()
    all_sales = Sale.query.filter_by(user_id=uid).all()
    recent_sales = Sale.query.filter_by(user_id=uid).order_by(Sale.sale_date.desc(), Sale.id.desc()).limit(8).all()
    recent_recs = PriceRecommendation.query.filter_by(user_id=uid).order_by(PriceRecommendation.generated_at.desc()).limit(6).all()

    total_products = len(products)
    total_revenue = sum(s.total_revenue for s in all_sales)
    total_units_sold = sum(s.quantity_sold for s in all_sales)
    avg_price = (sum(p.current_price for p in products) / total_products) if total_products > 0 else 0.0
    pending_recs = PriceRecommendation.query.filter_by(user_id=uid, status="Pending").count()

    metrics = get_model_metrics()

    return render_template(
        "index.html",
        total_products=total_products,
        total_revenue=round(total_revenue, 2),
        total_units_sold=total_units_sold,
        avg_price=round(avg_price, 2),
        pending_recs=pending_recs,
        recent_sales=recent_sales,
        recent_recs=recent_recs,
        metrics=metrics,
        user_sales_count=len(all_sales)
    )


# -------------------------------------------------------------
# MODULE 2: REAL PRODUCT MANAGEMENT (CRUD)
# -------------------------------------------------------------
@app.route("/products")
@login_required
def products():
    """View only the logged-in user's products."""
    uid = session["user_id"]
    user_prods = Product.query.filter_by(user_id=uid).order_by(Product.id.asc()).all()
    return render_template("products.html", products=user_prods)


@app.route("/products/add", methods=["POST"])
@login_required
def add_product():
    """Add a new product owned by the logged-in user."""
    uid = session["user_id"]
    try:
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "General").strip()
        cost_price = float(request.form.get("cost_price", 0.0))
        base_price = float(request.form.get("base_price", 0.0))
        current_price = float(request.form.get("current_price", base_price))

        competitor_price = float(request.form.get("competitor_price", base_price))
        inventory_level = int(request.form.get("inventory_level", 50))
        demand_level = int(request.form.get("demand_level", 2))
        season = int(request.form.get("season", 1))

        if not name or cost_price <= 0 or base_price <= 0:
            flash("Please provide a valid product name and positive prices.", "danger")
            return redirect(url_for("products"))

        new_prod = Product(
            user_id=uid,
            name=name,
            category=category,
            cost_price=cost_price,
            base_price=base_price,
            current_price=current_price
        )
        db.session.add(new_prod)
        db.session.flush()

        # Create initial market entry tied to user and product
        market = MarketData(
            user_id=uid,
            product_id=new_prod.id,
            competitor_price=competitor_price,
            demand_level=demand_level,
            inventory_level=inventory_level,
            season=season,
            recorded_date=date.today()
        )
        db.session.add(market)
        db.session.commit()

        flash(f"Product '{name}' saved permanently to MySQL under your account!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding product: {str(e)}", "danger")

    return redirect(url_for("products"))


@app.route("/products/edit/<int:product_id>", methods=["POST"])
@login_required
def edit_product(product_id):
    """Edit an existing product (Ownership verified)."""
    uid = session["user_id"]
    prod = Product.query.filter_by(id=product_id, user_id=uid).first()
    if not prod:
        flash("Unauthorized: You can only edit your own products.", "danger")
        return redirect(url_for("products"))

    try:
        prod.name = request.form.get("name", prod.name).strip()
        prod.category = request.form.get("category", prod.category).strip()
        prod.cost_price = float(request.form.get("cost_price", prod.cost_price))
        prod.base_price = float(request.form.get("base_price", prod.base_price))
        prod.current_price = float(request.form.get("current_price", prod.current_price))

        db.session.commit()
        flash(f"Product '{prod.name}' updated successfully in MySQL!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating product: {str(e)}", "danger")

    return redirect(url_for("products"))


@app.route("/products/delete/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    """Delete a product (Ownership verified)."""
    uid = session["user_id"]
    prod = Product.query.filter_by(id=product_id, user_id=uid).first()
    if not prod:
        flash("Unauthorized: You can only delete your own products.", "danger")
        return redirect(url_for("products"))

    try:
        name = prod.name
        db.session.delete(prod)
        db.session.commit()
        flash(f"Product '{name}' and its related records deleted successfully.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting product: {str(e)}", "danger")

    return redirect(url_for("products"))


# -------------------------------------------------------------
# MODULE 3: REAL SALES DATA
# -------------------------------------------------------------
@app.route("/sales")
@login_required
def sales():
    """View logged-in user's sales log and products."""
    uid = session["user_id"]
    user_sales = Sale.query.filter_by(user_id=uid).order_by(Sale.sale_date.desc(), Sale.id.desc()).all()
    user_products = Product.query.filter_by(user_id=uid).order_by(Product.name.asc()).all()
    return render_template("sales.html", sales=user_sales, products=user_products)


@app.route("/sales/add", methods=["POST"])
@login_required
def add_sale():
    """Record a real sales transaction in MySQL (Ownership verified)."""
    uid = session["user_id"]
    try:
        product_id = int(request.form.get("product_id"))
        prod = Product.query.filter_by(id=product_id, user_id=uid).first()
        if not prod:
            flash("Unauthorized: Selected product does not belong to your account.", "danger")
            return redirect(url_for("sales"))

        quantity = int(request.form.get("quantity_sold", 1))
        selling_price = float(request.form.get("selling_price", prod.current_price))
        sale_date_str = request.form.get("sale_date")

        if sale_date_str:
            sale_date = datetime.strptime(sale_date_str, "%Y-%m-%d").date()
        else:
            sale_date = date.today()

        total_rev = round(quantity * selling_price, 2)
        new_sale = Sale(
            user_id=uid,
            product_id=product_id,
            quantity_sold=quantity,
            selling_price=selling_price,
            total_revenue=total_rev,
            sale_date=sale_date
        )
        db.session.add(new_sale)

        # Update latest inventory if available
        market = MarketData.query.filter_by(user_id=uid, product_id=product_id).order_by(MarketData.id.desc()).first()
        if market and market.inventory_level >= quantity:
            market.inventory_level -= quantity

        db.session.commit()
        flash(f"Sale recorded in MySQL: {quantity}x '{prod.name}' for ${total_rev:.2f}", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error logging sale: {str(e)}", "danger")

    return redirect(url_for("sales"))


# -------------------------------------------------------------
# MODULE 4: REAL MARKET & INVENTORY DATA
# -------------------------------------------------------------
@app.route("/market")
@login_required
def market():
    """View and update competitor prices and inventory for user products."""
    uid = session["user_id"]
    user_products = Product.query.filter_by(user_id=uid).all()
    market_entries = []

    for p in user_products:
        latest_market = MarketData.query.filter_by(
            user_id=uid, product_id=p.id
        ).order_by(MarketData.recorded_date.desc(), MarketData.id.desc()).first()
        market_entries.append({
            "product": p,
            "market": latest_market
        })

    return render_template("market.html", entries=market_entries)


@app.route("/market/update/<int:product_id>", methods=["POST"])
@login_required
def update_market(product_id):
    """Update market conditions (Ownership verified)."""
    uid = session["user_id"]
    prod = Product.query.filter_by(id=product_id, user_id=uid).first()
    if not prod:
        flash("Unauthorized: Selected product does not belong to your account.", "danger")
        return redirect(url_for("market"))

    try:
        competitor_price = float(request.form.get("competitor_price", 0.0))
        demand_level = int(request.form.get("demand_level", 2))
        inventory_level = int(request.form.get("inventory_level", 50))
        season = int(request.form.get("season", 1))

        latest_market = MarketData.query.filter_by(
            user_id=uid, product_id=product_id
        ).order_by(MarketData.id.desc()).first()

        if latest_market:
            latest_market.competitor_price = competitor_price
            latest_market.demand_level = demand_level
            latest_market.inventory_level = inventory_level
            latest_market.season = season
            latest_market.recorded_date = date.today()
        else:
            new_market = MarketData(
                user_id=uid,
                product_id=product_id,
                competitor_price=competitor_price,
                demand_level=demand_level,
                inventory_level=inventory_level,
                season=season,
                recorded_date=date.today()
            )
            db.session.add(new_market)

        db.session.commit()
        flash("Market conditions saved in MySQL! Ready for AI price optimization.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating market data: {str(e)}", "danger")

    return redirect(url_for("market"))


# -------------------------------------------------------------
# MODULE 5 & 6: DYNAMIC PRICE OPTIMIZATION
# -------------------------------------------------------------
@app.route("/pricing")
@login_required
def pricing():
    """Price Optimization Hub - Scoped strictly to logged-in user."""
    uid = session["user_id"]
    user_products = Product.query.filter_by(user_id=uid).order_by(Product.name.asc()).all()

    selected_id = request.args.get("product_id", type=int)
    selected_prod = None
    selected_market = None
    latest_rec = None

    if selected_id:
        selected_prod = Product.query.filter_by(id=selected_id, user_id=uid).first()
        if selected_prod:
            selected_market = MarketData.query.filter_by(
                user_id=uid, product_id=selected_id
            ).order_by(MarketData.id.desc()).first()
            latest_rec = PriceRecommendation.query.filter_by(
                user_id=uid, product_id=selected_id
            ).order_by(PriceRecommendation.id.desc()).first()

    all_recs = PriceRecommendation.query.filter_by(user_id=uid).order_by(
        PriceRecommendation.generated_at.desc()
    ).all()

    return render_template(
        "pricing.html",
        products=user_products,
        selected_prod=selected_prod,
        selected_market=selected_market,
        latest_rec=latest_rec,
        all_recs=all_recs
    )


@app.route("/pricing/recommend/<int:product_id>", methods=["POST"])
@login_required
def recommend_price_action(product_id):
    """Executes ML Price Optimization on user's product (Ownership verified)."""
    uid = session["user_id"]
    prod = Product.query.filter_by(id=product_id, user_id=uid).first()
    if not prod:
        flash("Unauthorized: Selected product does not belong to your account.", "danger")
        return redirect(url_for("pricing"))

    latest_market = MarketData.query.filter_by(
        user_id=uid, product_id=product_id
    ).order_by(MarketData.id.desc()).first()

    comp_price = latest_market.competitor_price if latest_market else prod.current_price
    demand_lvl = latest_market.demand_level if latest_market else 2
    inv_lvl = latest_market.inventory_level if latest_market else 50
    season = latest_market.season if latest_market else 1

    # Real historical average sales for this user's product
    recent_sales = Sale.query.filter_by(user_id=uid, product_id=product_id).limit(10).all()
    avg_qty = int(sum(s.quantity_sold for s in recent_sales) / len(recent_sales)) if recent_sales else 20

    # Execute ML Inference with Safety Guardrails
    result = predict_optimal_price(
        cost_price=prod.cost_price,
        current_price=prod.current_price,
        competitor_price=comp_price,
        demand_level=demand_lvl,
        inventory_level=inv_lvl,
        season=season,
        quantity_sold=avg_qty
    )

    # Save to price_recommendations table in MySQL
    rec = PriceRecommendation(
        user_id=uid,
        product_id=prod.id,
        current_price=prod.current_price,
        recommended_price=result["recommended_price"],
        price_difference=result["price_difference"],
        confidence_score=result["confidence_score"],
        reason=result["reason"],
        status="Pending"
    )
    db.session.add(rec)
    db.session.commit()

    flash(
        f"AI Recommendation saved: '{prod.name}' -> ${result['recommended_price']:.2f} "
        f"({result['price_difference']:+.2f})",
        "success"
    )
    return redirect(url_for("pricing", product_id=prod.id))


@app.route("/pricing/apply/<int:rec_id>", methods=["POST"])
@login_required
def apply_price_action(rec_id):
    """Applies recommended price to active product in MySQL (Ownership verified)."""
    uid = session["user_id"]
    rec = PriceRecommendation.query.filter_by(id=rec_id, user_id=uid).first()
    if not rec:
        flash("Unauthorized: Recommendation not found in your account.", "danger")
        return redirect(url_for("pricing"))

    prod = Product.query.filter_by(id=rec.product_id, user_id=uid).first()
    if not prod:
        flash("Unauthorized: Associated product not found.", "danger")
        return redirect(url_for("pricing"))

    old_price = prod.current_price
    new_price = rec.recommended_price

    prod.current_price = new_price
    rec.status = "Applied"
    db.session.commit()

    flash(
        f"Price Applied in MySQL! '{prod.name}' updated from ${old_price:.2f} to ${new_price:.2f}.",
        "success"
    )
    return redirect(url_for("pricing", product_id=prod.id))


# -------------------------------------------------------------
# DEMO DATA LOADER (FOR USER'S ACCOUNT)
# -------------------------------------------------------------
@app.route("/user/load-demo-data", methods=["POST"])
@login_required
def load_user_demo_data():
    """Seeds starter sample products specifically into the logged-in user's account."""
    uid = session["user_id"]
    existing_count = Product.query.filter_by(user_id=uid).count()
    if existing_count > 0:
        flash("Your account already contains products.", "info")
        return redirect(url_for("index"))

    starter_items = [
        {"name": "Wireless Noise-Canceling Headphones", "category": "Electronics", "cost": 45.0, "base": 99.99, "curr": 99.99, "comp": 105.0, "inv": 35, "dem": 3, "sea": 4},
        {"name": "Smart Fitness Watch", "category": "Electronics", "cost": 30.0, "base": 69.99, "curr": 69.99, "comp": 64.99, "inv": 110, "dem": 2, "sea": 3},
        {"name": "Ergonomic Office Chair", "category": "Furniture", "cost": 75.0, "base": 179.99, "curr": 179.99, "comp": 185.0, "inv": 25, "dem": 3, "sea": 1},
        {"name": "Compact Cold Brew Coffee Maker", "category": "Home & Kitchen", "cost": 15.0, "base": 39.99, "curr": 39.99, "comp": 42.0, "inv": 40, "dem": 3, "sea": 2}
    ]

    for item in starter_items:
        p = Product(
            user_id=uid,
            name=item["name"],
            category=item["category"],
            cost_price=item["cost"],
            base_price=item["base"],
            current_price=item["curr"]
        )
        db.session.add(p)
        db.session.flush()

        m = MarketData(
            user_id=uid,
            product_id=p.id,
            competitor_price=item["comp"],
            demand_level=item["dem"],
            inventory_level=item["inv"],
            season=item["sea"],
            recorded_date=date.today()
        )
        db.session.add(m)

    db.session.commit()
    flash("Demo catalog loaded into your MySQL account! You can now test pricing optimization.", "success")
    return redirect(url_for("index"))


# -------------------------------------------------------------
# MODULE 7: REPORTS & ANALYTICS
# -------------------------------------------------------------
@app.route("/reports")
@login_required
def reports():
    """Visual reports & analytical trends."""
    metrics = get_model_metrics()
    return render_template("reports.html", metrics=metrics)


# -------------------------------------------------------------
# CHART.JS REST API ENDPOINTS (Scoped strictly by user_id)
# -------------------------------------------------------------
@app.route("/api/chart/sales-trends")
@login_required
def api_sales_trends():
    """Returns aggregated historical sales data for logged-in user."""
    uid = session["user_id"]
    sales = Sale.query.filter_by(user_id=uid).order_by(Sale.sale_date.asc()).all()
    aggregated = {}
    for s in sales:
        date_key = s.sale_date.strftime("%b %d")
        if date_key not in aggregated:
            aggregated[date_key] = {"revenue": 0.0, "units": 0}
        aggregated[date_key]["revenue"] += s.total_revenue
        aggregated[date_key]["units"] += s.quantity_sold

    labels = list(aggregated.keys())
    revenues = [round(v["revenue"], 2) for v in aggregated.values()]
    units = [v["units"] for v in aggregated.values()]

    return jsonify({
        "labels": labels,
        "revenues": revenues,
        "units": units
    })


@app.route("/api/chart/price-comparison")
@login_required
def api_price_comparison():
    """Returns Current Price vs Competitor vs Recommended for user's products."""
    uid = session["user_id"]
    products = Product.query.filter_by(user_id=uid).all()
    labels = []
    current_prices = []
    competitor_prices = []
    recommended_prices = []

    for p in products:
        labels.append(p.name[:20] + ("..." if len(p.name) > 20 else ""))
        current_prices.append(round(p.current_price, 2))

        m = MarketData.query.filter_by(
            user_id=uid, product_id=p.id
        ).order_by(MarketData.id.desc()).first()
        competitor_prices.append(round(m.competitor_price, 2) if m else round(p.current_price, 2))

        r = PriceRecommendation.query.filter_by(
            user_id=uid, product_id=p.id
        ).order_by(PriceRecommendation.id.desc()).first()
        recommended_prices.append(round(r.recommended_price, 2) if r else round(p.current_price, 2))

    return jsonify({
        "labels": labels,
        "current_prices": current_prices,
        "competitor_prices": competitor_prices,
        "recommended_prices": recommended_prices
    })


@app.route("/api/chart/category-distribution")
@login_required
def api_category_distribution():
    """Returns product count by category for logged-in user."""
    uid = session["user_id"]
    products = Product.query.filter_by(user_id=uid).all()
    cats = {}
    for p in products:
        cats[p.category] = cats.get(p.category, 0) + 1

    return jsonify({
        "labels": list(cats.keys()),
        "counts": list(cats.values())
    })


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("   DYNAMIC PRICE OPTIMIZATION ENGINE IS RUNNING")
    print("   Multi-User Authentication & Strict MySQL Active")
    print("   Access at: http://127.0.0.1:5000")
    print("=" * 65 + "\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
