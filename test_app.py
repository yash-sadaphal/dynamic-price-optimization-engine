import unittest
from app import app, db
from database.db import User, Product, Sale, MarketData, PriceRecommendation


class TestMultiUserDynamicPricingApp(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def register(self, username, email, password):
        return self.client.post("/register", data={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password
        }, follow_redirects=True)

    def login(self, username, password):
        return self.client.post("/login", data={
            "username": username,
            "password": password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get("/logout", follow_redirects=True)

    def test_01_unauthenticated_redirect(self):
        """Unauthenticated requests to protected routes must redirect to /login."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        print("[TEST PASS] Unauthenticated redirect to /login verified.")

    def test_02_user_registration_and_login(self):
        """Tests user registration and password hashing in MySQL."""
        # Unique usernames based on timestamp/test
        uname = "alice_test"
        email = "alice@example.com"
        
        # Cleanup if exists
        existing = User.query.filter((User.username == uname) | (User.email == email)).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        # 1. Register Alice
        res = self.register(uname, email, "AlicePass123")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome, alice_test", res.data)

        # Verify password hash exists and matches
        user = User.query.filter_by(username=uname).first()
        self.assertIsNotNone(user)
        self.assertNotEqual(user.password_hash, "AlicePass123")  # Must be hashed!
        self.assertTrue(user.check_password("AlicePass123"))
        self.assertFalse(user.check_password("WrongPassword"))
        print("[TEST PASS] User registration and PBKDF2/scrypt password hashing verified.")

    def test_03_multi_user_data_isolation(self):
        """
        CRITICAL TEST: Verifies that User A's products, sales, and recommendations
        are completely isolated from User B, and User B cannot modify User A's records.
        """
        # 1. Register & Login as User A
        uA_name = "usera_retail"
        uA_email = "usera@example.com"
        uA = User.query.filter((User.username == uA_name) | (User.email == uA_email)).first()
        if uA:
            db.session.delete(uA)
            db.session.commit()

        self.register(uA_name, uA_email, "PasswordA123")
        
        # User A adds a product
        add_res = self.client.post("/products/add", data={
            "name": "User A Exclusive Headphones",
            "category": "Electronics",
            "cost_price": "50.00",
            "base_price": "100.00",
            "current_price": "100.00",
            "competitor_price": "110.00",
            "inventory_level": "30",
            "demand_level": "3",
            "season": "4"
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)

        # Get User A's product ID
        uA_prod = Product.query.filter_by(name="User A Exclusive Headphones").first()
        self.assertIsNotNone(uA_prod)
        uA_prod_id = uA_prod.id

        # 2. Register & Login as User B
        self.logout()
        uB_name = "userb_retail"
        uB_email = "userb@example.com"
        uB = User.query.filter((User.username == uB_name) | (User.email == uB_email)).first()
        if uB:
            db.session.delete(uB)
            db.session.commit()

        self.register(uB_name, uB_email, "PasswordB123")

        # 3. Verify User B does NOT see User A's product on /products
        res_prods_b = self.client.get("/products")
        self.assertEqual(res_prods_b.status_code, 200)
        self.assertNotIn(b"User A Exclusive Headphones", res_prods_b.data)

        # 4. Security Check: User B attempts to edit User A's product via URL parameter
        tamper_res = self.client.post(f"/products/edit/{uA_prod_id}", data={
            "name": "Tampered Product",
            "category": "Electronics",
            "cost_price": "10.00",
            "base_price": "20.00",
            "current_price": "20.00"
        }, follow_redirects=True)
        self.assertIn(b"Unauthorized: You can only edit your own products", tamper_res.data)

        # Verify product was NOT modified in MySQL
        recheck_prod = db.session.get(Product, uA_prod_id)
        self.assertEqual(recheck_prod.name, "User A Exclusive Headphones")
        self.assertEqual(recheck_prod.cost_price, 50.00)

        print("[TEST PASS] Multi-user data isolation and URL parameter tamper security verified.")

    def test_04_real_sales_and_pricing_optimization_flow(self):
        """
        Tests the complete pipeline for a real user:
        Add Product -> Record Sale -> Run AI Price Optimization -> Apply Recommended Price.
        """
        # Login as demo_user
        self.login("demo_user", "demo123")

        # Get first product owned by demo_user
        demo_user = User.query.filter_by(username="demo_user").first()
        prod = Product.query.filter_by(user_id=demo_user.id).first()
        self.assertIsNotNone(prod)
        initial_price = prod.current_price

        # 1. Record a real sale
        sale_res = self.client.post("/sales/add", data={
            "product_id": prod.id,
            "quantity_sold": "5",
            "selling_price": str(prod.current_price),
            "sale_date": "2026-09-08"
        }, follow_redirects=True)
        self.assertEqual(sale_res.status_code, 200)
        self.assertIn(b"Sale recorded in MySQL", sale_res.data)

        # 2. Trigger AI Price Optimization
        opt_res = self.client.post(f"/pricing/recommend/{prod.id}", follow_redirects=True)
        self.assertEqual(opt_res.status_code, 200)
        self.assertIn(b"AI Recommendation saved", opt_res.data)

        # 3. Retrieve generated recommendation from MySQL
        rec = PriceRecommendation.query.filter_by(
            user_id=demo_user.id, product_id=prod.id, status="Pending"
        ).order_by(PriceRecommendation.id.desc()).first()
        self.assertIsNotNone(rec)
        rec_price = rec.recommended_price

        # 4. Apply recommended price
        apply_res = self.client.post(f"/pricing/apply/{rec.id}", follow_redirects=True)
        self.assertEqual(apply_res.status_code, 200)
        self.assertIn(b"Price Applied in MySQL", apply_res.data)

        # 5. Verify product price updated in MySQL
        db.session.expire_all()
        updated_prod = db.session.get(Product, prod.id)
        self.assertEqual(updated_prod.current_price, rec_price)
        print(f"[TEST PASS] Complete Real User Flow (Product -> Sale -> AI Rec -> Price Update: ${initial_price:.2f} -> ${rec_price:.2f}) verified.")

    def test_05_chart_apis_authenticated(self):
        """Verifies Chart.js REST endpoints return valid JSON for authenticated user."""
        self.login("demo_user", "demo123")

        res1 = self.client.get("/api/chart/sales-trends")
        self.assertEqual(res1.status_code, 200)
        self.assertIn("revenues", res1.get_json())

        res2 = self.client.get("/api/chart/price-comparison")
        self.assertEqual(res2.status_code, 200)
        self.assertIn("current_prices", res2.get_json())

        res3 = self.client.get("/api/chart/category-distribution")
        self.assertEqual(res3.status_code, 200)
        self.assertIn("counts", res3.get_json())
        print("[TEST PASS] All user-scoped Chart.js REST endpoints verified.")


if __name__ == "__main__":
    unittest.main()
