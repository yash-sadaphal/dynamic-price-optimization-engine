import os
import sys
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from config import Config
from database.db import db, Product, Sale, MarketData

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_CSV = os.path.join(BASE_DIR, "data", "sample_data.csv")
MODEL_FILE = os.path.join(MODELS_DIR, "price_model.pkl")
METRICS_FILE = os.path.join(MODELS_DIR, "metrics.json")

os.makedirs(MODELS_DIR, exist_ok=True)

# Define feature columns used for training
FEATURE_COLS = [
    "cost_price",
    "current_price",
    "competitor_price",
    "demand_level",
    "inventory_level",
    "season",
    "quantity_sold"
]
TARGET_COL = "optimal_selling_price"


def load_training_data():
    """
    Attempts to load training data from the database.
    If the database contains insufficient records, loads from sample_data.csv.
    """
    print("[DATA] Loading training dataset...")
    if os.path.exists(DATA_CSV):
        df = pd.read_csv(DATA_CSV)
        print(f"[DATA] Loaded {len(df)} records from {DATA_CSV}")
        return df
    else:
        raise FileNotFoundError(f"Training data not found at {DATA_CSV}. Run ml/generate_sample_data.py first.")


def train():
    """
    Trains the Price Optimization Model:
    1. Splits dataset into 80% train and 20% test sets.
    2. Scales numerical features using StandardScaler.
    3. Trains Linear Regression (baseline) and Random Forest Regressor.
    4. Computes MAE, RMSE, and R2 evaluation metrics.
    5. Saves the champion model and scaler to models/price_model.pkl.
    """
    print("=" * 60)
    print("      DYNAMIC PRICE OPTIMIZATION - MODEL TRAINING")
    print("=" * 60)

    # 1. Load Data
    df = load_training_data()

    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    print(f"[PREPROCESSING] Feature columns ({len(FEATURE_COLS)}): {FEATURE_COLS}")
    print(f"[PREPROCESSING] Target column: '{TARGET_COL}'")

    # 2. Train-Test Split (80% Training, 20% Testing)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    print(f"[SPLIT] Training samples: {len(X_train)}, Testing samples: {len(X_test)}")

    # 3. Feature Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 4. Train Baseline Model (Linear Regression)
    lr_model = LinearRegression()
    lr_model.fit(X_train_scaled, y_train)
    lr_preds = lr_model.predict(X_test_scaled)

    lr_mae = mean_absolute_error(y_test, lr_preds)
    lr_rmse = np.sqrt(mean_squared_error(y_test, lr_preds))
    lr_r2 = r2_score(y_test, lr_preds)

    print("\n--- Baseline Model: Linear Regression ---")
    print(f"  * Mean Absolute Error (MAE):    ${lr_mae:.2f}")
    print(f"  * Root Mean Squared Error (RMSE): ${lr_rmse:.2f}")
    print(f"  * R-squared (R2 Score):          {lr_r2:.4f} ({lr_r2*100:.2f}%)")

    # 5. Train Champion Model (Random Forest Regressor)
    rf_model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42
    )
    rf_model.fit(X_train_scaled, y_train)
    rf_preds = rf_model.predict(X_test_scaled)

    rf_mae = mean_absolute_error(y_test, rf_preds)
    rf_rmse = np.sqrt(mean_squared_error(y_test, rf_preds))
    rf_r2 = r2_score(y_test, rf_preds)

    print("\n--- Primary Model: Random Forest Regressor ---")
    print(f"  * Mean Absolute Error (MAE):    ${rf_mae:.2f}")
    print(f"  * Root Mean Squared Error (RMSE): ${rf_rmse:.2f}")
    print(f"  * R-squared (R2 Score):          {rf_r2:.4f} ({rf_r2*100:.2f}%)")

    # Feature Importance analysis
    importances = dict(zip(FEATURE_COLS, [round(float(val), 4) for val in rf_model.feature_importances_]))
    print("\n[VIVA INSIGHT] Feature Importances (Random Forest):")
    for feat, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {feat.ljust(18)}: {imp * 100:.1f}%")

    # 6. Save Champion Model & Artifacts
    package = {
        "model": rf_model,
        "scaler": scaler,
        "features": FEATURE_COLS,
        "model_type": "RandomForestRegressor",
        "r2_score": float(rf_r2),
        "mae": float(rf_mae),
        "rmse": float(rf_rmse)
    }

    joblib.dump(package, MODEL_FILE)
    print(f"\n[SAVED] Champion model saved to: {MODEL_FILE}")

    metrics = {
        "linear_regression": {
            "mae": round(float(lr_mae), 2),
            "rmse": round(float(lr_rmse), 2),
            "r2_score": round(float(lr_r2), 4)
        },
        "random_forest": {
            "mae": round(float(rf_mae), 2),
            "rmse": round(float(rf_rmse), 2),
            "r2_score": round(float(rf_r2), 4),
            "feature_importance": importances
        },
        "trained_samples": len(df),
        "features": FEATURE_COLS
    }

    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f, indent=4)
    print(f"[SAVED] Metrics report saved to: {METRICS_FILE}")
    print("=" * 60)
    print("Training successfully completed!\n")

    return package


if __name__ == "__main__":
    train()
