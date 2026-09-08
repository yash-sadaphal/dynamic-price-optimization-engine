# Dynamic Price Optimization Engine using AI & Machine Learning
### Applied Machine Learning for Industry Solutions Laboratory Project

A production-grade, multi-user web application designed to predict and recommend optimal product selling prices in real time. Built with Python, Flask, MySQL, SQLAlchemy, Scikit-learn, Bootstrap 5, and Chart.js.

---

## 📋 Table of Contents
1. [Project Overview & Viva Architecture](#project-overview--viva-architecture)
2. [Multi-User Architecture & Security](#multi-user-architecture--security)
3. [Technology Stack](#technology-stack)
4. [Project Folder Structure](#project-folder-structure)
5. [Database Schema in MySQL (`dynamic_price_db`)](#database-schema-in-mysql-dynamic_price_db)
6. [Machine Learning Workflow](#machine-learning-workflow)
7. [How to Run in VS Code (Step-by-Step)](#how-to-run-in-vs-code-step-by-step)
8. [Automated Testing & Verification](#automated-testing--verification)
9. [Comprehensive Viva / Oral Examination Guide](#comprehensive-viva--oral-examination-guide)

---

## 🚀 Project Overview & Viva Architecture

Dynamic pricing is used across modern industries (e.g., Amazon, Uber, airlines) to dynamically adjust prices according to supply and demand conditions.

### Core Mathematical Rationale
The fundamental objective of dynamic pricing is revenue maximization:
$$\text{Revenue} = \text{Selling Price} \times \text{Quantity Sold}$$

By the economic law of demand, increasing price reduces sales volume (Price Elasticity of Demand). The Machine Learning model learns the non-linear inflection point where price, competitor benchmarks, inventory scarcity, and demand produce the highest expected revenue without sacrificing profit margin.

```
       +-------------------------------------------------------------+
       |                     INPUT SIGNALS                           |
       |  • Base / Cost Price        • Competitor Price             |
       |  • Inventory Scarcity       • Consumer Demand Level (1-3)   |
       |  • Seasonal Spikes (1-4)    • Historical Sales Velocity     |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |             MACHINE LEARNING INFERENCE ENGINE               |
       |       Random Forest Regressor (R² Accuracy: 99.47%)         |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                 BUSINESS SAFETY GUARDRAILS                  |
       |  1. Margin Floor:  Price >= Cost Price x 1.12 (Min 12% ROI) |
       |  2. Volatility:    Capped within +/- 25% of Current Price   |
       +------------------------------+------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |            OPTIMAL SELLING PRICE RECOMMENDATION             |
       |     • AI Price Recommendation    • Explainable Rationale    |
       |     • Variance ($ & %)           • 1-Click Catalog Apply    |
       +-------------------------------------------------------------+
```

---

## 🔐 Multi-User Architecture & Security

1. **User Authentication**:
   - Secure registration and login (`/register`, `/login`, `/logout`).
   - Passwords hashed using industry-standard PBKDF2/scrypt (`werkzeug.security`).
   - Plain-text passwords are never stored in the database.
   - Session-based authentication with `@login_required` route decorator.

2. **Multi-Tenant Data Isolation**:
   - Every product, sale, market observation, and AI recommendation belongs to a specific user (`user_id` foreign key).
   - User A can only see and manage User A's products and sales.
   - User B sees only User B's records.
   - **Tamper Protection**: Attempting to edit or delete another user's product by manipulating the URL parameter is intercepted and rejected with an unauthorized warning.

3. **Separation of Sample Data vs Real Business Data**:
   - `data/sample_data.csv` is preserved strictly as the baseline retail elasticity dataset used for training the core ML model.
   - Real user business records are stored permanently in MySQL under their respective user accounts.
   - Empty state guidance is provided for new users with the option to add real products or load a starter demo catalog into their account.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | Python 3, Flask | Web server, session authentication, and REST APIs |
| **Database** | MySQL 8.0, SQLAlchemy | Relational storage for users, products, sales, and recommendations |
| **DB Driver** | PyMySQL, Cryptography | Pure-Python MySQL connectivity with MySQL 8 caching_sha2 authentication |
| **Machine Learning** | Scikit-learn, Pandas, NumPy | Data preprocessing, Random Forest training, evaluation, and inference |
| **Frontend** | HTML5, Modern CSS, Bootstrap 5 | Clean, responsive UI with KPI cards, modals, and user profile management |
| **Visualizations** | Chart.js | Real-time trends, grouped competitor price bars, and revenue velocity |

---

## 📂 Project Folder Structure

```
dynamic_price_optimization/
│
├── app.py                      # Flask backend entry point & modular authenticated routes
├── config.py                   # App configuration & strict MySQL connection handler
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation & viva guide
├── test_app.py                 # Multi-user automated test suite
├── .env                        # Environment variables (MySQL credentials: root / yash@123)
│
├── models/
│   ├── price_model.pkl         # Serialized Scikit-learn Random Forest model & scaler
│   └── metrics.json            # Model evaluation metrics (R², MAE, RMSE, feature importances)
│
├── ml/
│   ├── __init__.py
│   ├── generate_sample_data.py # Baseline synthetic retail pricing dataset generator
│   ├── train_model.py          # Training pipeline comparing Linear Regression vs Random Forest
│   └── predict_price.py        # Inference engine with business guardrails & explainable AI
│
├── database/
│   ├── __init__.py
│   ├── db.py                   # SQLAlchemy model definitions (User, Product, Sale, MarketData, Recs)
│   └── init_mysql.py           # MySQL table initialization script & demo account creator
│
├── templates/
│   ├── base.html               # Master layout with user profile dropdown & dynamic sidebar
│   ├── login.html              # Sign in page
│   ├── register.html           # User registration page
│   ├── index.html              # Module 1: User Dashboard with KPI cards & Chart.js
│   ├── products.html           # Module 2: Product Catalog CRUD (Add, Edit, Delete, View)
│   ├── sales.html              # Module 3: Historical Sales log & transaction recorder
│   ├── market.html             # Module 4: Market intelligence (Competitor, Demand, Inventory)
│   ├── pricing.html            # Module 6: Dynamic Price Optimization & 1-Click Apply
│   └── reports.html            # Module 7: Analytical reports & viva presentation metrics
│
├── static/
│   ├── css/
│   │   └── style.css           # Modern custom stylesheet
│   └── js/
│       └── charts.js           # Asynchronous Chart.js rendering scripts
│
└── data/
    └── sample_data.csv         # 800 synthetic retail training records
```

---

## 🗄️ Database Schema in MySQL (`dynamic_price_db`)

The database consists of 5 relational tables:

```
  +---------------+
  |     users     |
  +---------------+
  | id (PK)       |
  | username      |
  | email         |
  | password_hash |
  | created_at    |
  +-------+-------+
          |
          +------------+--------------------+--------------------+
          | 1:N        | 1:N                | 1:N                | 1:N
          v            v                    v                    v
  +---------------+  +---------------+  +---------------+  +---------------------+
  |   products    |  |     sales     |  |  market_data  |  |price_recommendations|
  +---------------+  +---------------+  +---------------+  +---------------------+
  | id (PK)       |  | id (PK)       |  | id (PK)       |  | id (PK)             |
  | user_id (FK)  |  | user_id (FK)  |  | user_id (FK)  |  | user_id (FK)         |
  | name          |  | product_id(FK)|  | product_id(FK)|  | product_id (FK)     |
  | category      |  | quantity_sold |  |competitor_pr  |  | current_price       |
  | cost_price    |  | selling_price |  | demand_level  |  | recommended_price   |
  | base_price    |  | total_revenue |  |inventory_level|  | price_difference    |
  | current_price |  | sale_date     |  | season        |  | confidence_score    |
  | created_at    |  +---------------+  | recorded_date |  | reason              |
  +---------------+                     +---------------+  | status              |
                                                           | generated_at        |
                                                           +---------------------+
```

---

## 💻 How to Run in VS Code (Step-by-Step)

### Step 1: Open VS Code Terminal
```powershell
cd d:\AIML
```

### Step 2: Activate Virtual Environment
```powershell
.venv\Scripts\Activate.ps1
```

### Step 3: Verify `.env` Configuration
Your `.env` is pre-configured with:
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yash@123
MYSQL_DB=dynamic_price_db
```

### Step 4: Run MySQL Initialization (One-Time Setup)
```powershell
python database/init_mysql.py
```
*Creates all 5 tables in `dynamic_price_db` and seeds starter account `demo_user` (`demo123`).*

### Step 5: Start Flask Application
```powershell
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

### Step 6: Test User Flow in Browser
1. Sign in with the demo account: `demo_user` / `demo123` (or click **Create New Account** to register your own user).
2. Go to **My Products** (`/products`) to add your real products.
3. Go to **My Sales Log** (`/sales`) to enter real transaction records.
4. Go to **Market Intel** (`/market`) to update competitor price, inventory, and demand.
5. Go to **Dynamic Pricing** (`/pricing`), select a product, and click **"Run AI Price Optimization"**.
6. Review the recommended price, variance ($ and %), and Explainable AI rationale, then click **"Apply Recommended Price"** to update your catalog in MySQL!
7. Register a second user account (`test_user_2`) and verify that User 1's products and sales are completely isolated.

---

## 🧪 Automated Testing & Verification

Run the comprehensive multi-user test suite:
```powershell
python test_app.py
```
**Output:**
```
Ran 5 tests in 3.361s

OK
[DATABASE] Connected successfully to MySQL database: 'dynamic_price_db' at localhost:3306
[TEST PASS] Unauthenticated redirect to /login verified.
[TEST PASS] User registration and PBKDF2/scrypt password hashing verified.
[TEST PASS] Multi-user data isolation and URL parameter tamper security verified.
[TEST PASS] Complete Real User Flow (Product -> Sale -> AI Rec -> Price Update) verified.
[TEST PASS] All user-scoped Chart.js REST endpoints verified.
```

---

## 🎓 Comprehensive Viva / Oral Examination Guide

### Q1: What makes this a real multi-user application?
> **Answer:** Every business entity (`products`, `sales`, `market_data`, `price_recommendations`) contains a `user_id` foreign key referencing the `users` table. When any user interacts with the app, queries are strictly filtered by their session user ID. If User B tries to modify User A's product by guessing the product ID in a POST URL, the server verifies ownership and blocks the request.

### Q2: How is user security implemented?
> **Answer:** Passwords are never stored in plain text. When a user registers, `werkzeug.security.generate_password_hash()` creates a cryptographically secure hash (PBKDF2/scrypt). During login, `check_password_hash()` verifies the password without decrypting. Sessions are stored in signed, tamper-resistant HTTP cookies. Protected routes are guarded by a custom `@login_required` decorator.

### Q3: How is real user data separated from sample data?
> **Answer:** `sample_data.csv` is used exclusively for training the baseline Machine Learning model. Real business data entered by users is stored permanently in the MySQL database under their respective `user_id`. The dashboard displays only the logged-in user's genuine business transactions and real catalog items.

### Q4: How does the ML model determine the optimal price?
> **Answer:** The engine uses a Random Forest Regressor trained on pricing features: cost price, current price, competitor price, demand level, inventory level, season, and sales velocity. It balances competitor benchmarks and demand elasticity, then applies business guardrails:
> 1. **Profit Floor Guardrail:** Price $\ge \text{Cost Price} \times 1.12$ (guaranteeing at least 12% gross profit margin).
> 2. **Volatility Cap Guardrail:** Price changes are capped to $\pm 25\%$ of current price to avoid customer sticker shock.
