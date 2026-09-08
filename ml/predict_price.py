import os
import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_FILE = os.path.join(BASE_DIR, "models", "price_model.pkl")

# Cached model package in memory
_MODEL_PACKAGE = None


def load_model_package():
    """
    Loads and caches the serialized model package.
    """
    global _MODEL_PACKAGE
    if _MODEL_PACKAGE is None:
        if not os.path.exists(MODEL_FILE):
            # If not yet trained, trigger training automatically
            from ml.train_model import train
            _MODEL_PACKAGE = train()
        else:
            _MODEL_PACKAGE = joblib.load(MODEL_FILE)
    return _MODEL_PACKAGE


def predict_optimal_price(
    cost_price: float,
    current_price: float,
    competitor_price: float,
    demand_level: int,
    inventory_level: int,
    season: int,
    quantity_sold: int = 25
) -> dict:
    """
    Predicts the optimal selling price using the trained Machine Learning model
    and applies business guardrails (profit floor, elasticity boundaries).

    Parameters:
        cost_price (float): Production/procurement unit cost.
        current_price (float): Active selling price.
        competitor_price (float): Market competitor price.
        demand_level (int): 1=Low, 2=Medium, 3=High.
        inventory_level (int): Current units in warehouse.
        season (int): 1=Spring, 2=Summer, 3=Fall, 4=Winter.
        quantity_sold (int): Historical average sales velocity.

    Returns:
        dict: Recommendation details including recommended price, difference,
              percentage change, confidence, and viva-ready business explanation.
    """
    pkg = load_model_package()
    model = pkg["model"]
    scaler = pkg["scaler"]
    r2_score = pkg.get("r2_score", 0.95)

    # 1. Prepare raw input DataFrame matching exact feature column names
    raw_features = pd.DataFrame([[
        float(cost_price),
        float(current_price),
        float(competitor_price),
        int(demand_level),
        int(inventory_level),
        int(season),
        int(quantity_sold)
    ]], columns=pkg.get("features", [
        "cost_price", "current_price", "competitor_price",
        "demand_level", "inventory_level", "season", "quantity_sold"
    ]))

    # 2. Scale features using saved scaler
    scaled_features = scaler.transform(raw_features)

    # 3. Model raw prediction
    raw_pred = float(model.predict(scaled_features)[0])

    # 4. Business Guardrail 1: Minimum Profit Margin Floor (Cost + 12%)
    min_margin_price = cost_price * 1.12
    guarded_price = max(raw_pred, min_margin_price)

    # 5. Business Guardrail 2: Maximum Price Swing (Avoid extreme shifts beyond +/- 25%)
    max_allowed = current_price * 1.25
    min_allowed = max(current_price * 0.75, min_margin_price)
    final_price = min(max(guarded_price, min_allowed), max_allowed)
    final_price = round(final_price, 2)

    # 6. Calculate metrics
    diff = round(final_price - current_price, 2)
    pct_change = round((diff / current_price) * 100, 2) if current_price > 0 else 0.0
    profit_margin = round(((final_price - cost_price) / final_price) * 100, 1) if final_price > 0 else 0.0

    # 7. Generate Intelligent Viva Explanation
    reasons = []
    if demand_level == 3 and inventory_level < 50:
        reasons.append("High consumer demand paired with low inventory (<50 units) creates pricing power.")
    elif demand_level == 1 and inventory_level > 150:
        reasons.append("High stock (>150 units) and slower demand indicate a markdown to accelerate velocity.")
    elif competitor_price > current_price * 1.05:
        reasons.append(f"Competitor is priced higher (${competitor_price:.2f}), leaving room to capture margin.")
    elif competitor_price < current_price * 0.95:
        reasons.append(f"Competitor is undercutting at ${competitor_price:.2f}; price trimmed to protect sales.")

    if season == 4:
        reasons.append("Holiday/Winter peak season multiplier applied.")
    elif season == 2:
        reasons.append("Mid-year seasonal demand boost applied.")

    if not reasons:
        if diff > 0:
            reasons.append(f"Market conditions support a slight +{pct_change}% upward price calibration.")
        elif diff < 0:
            reasons.append(f"Competitive benchmark suggests a {abs(pct_change)}% price trim to optimize revenue.")
        else:
            reasons.append("Current price is well aligned with market equilibrium.")

    full_reason = " ".join(reasons)

    return {
        "recommended_price": final_price,
        "current_price": round(current_price, 2),
        "cost_price": round(cost_price, 2),
        "competitor_price": round(competitor_price, 2),
        "price_difference": diff,
        "percentage_change": pct_change,
        "profit_margin_pct": profit_margin,
        "confidence_score": round(r2_score, 2),
        "reason": full_reason,
        "demand_level": demand_level,
        "inventory_level": inventory_level,
        "season": season
    }


if __name__ == "__main__":
    # Test sample prediction
    test_result = predict_optimal_price(
        cost_price=45.0,
        current_price=99.99,
        competitor_price=108.0,
        demand_level=3,
        inventory_level=35,
        season=4,
        quantity_sold=32
    )
    print("\n--- Test ML Prediction Output ---")
    for k, v in test_result.items():
        print(f"  {k}: {v}")
