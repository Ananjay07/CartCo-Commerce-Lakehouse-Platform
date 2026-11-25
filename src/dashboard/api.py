import os
import sys
import pandas as pd
import random
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="CartCo Lakehouse Dashboard API")

# Attempt to load PySpark
def get_spark():
    if not os.environ.get("SPARK_HOME") and not os.path.exists("/opt/airflow"):
        return None
    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from jobs.spark_helper import get_spark_session
        return get_spark_session("Dashboard-API")
    except Exception as e:
        print(f"Failed to initialize Spark session: {e}")
        return None

def generate_mock_gold_data():
    """Generates synthetic Gold mart data for offline rendering."""
    # Daily Revenue
    channels = ["shopify", "pos", "distributor"]
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(14)]
    
    rev_rows = []
    for d in dates:
        for c in channels:
            if c == "shopify":
                orders = random.randint(50, 150)
                rev = orders * random.uniform(800.0, 1200.0)
            elif c == "pos":
                orders = random.randint(100, 300)
                rev = orders * random.uniform(500.0, 700.0)
            else: # distributor
                orders = random.randint(2, 8)
                rev = orders * random.uniform(25000.0, 75000.0)
                
            tax = rev * 0.18
            rev_rows.append({
                "sales_date": d,
                "channel": c,
                "order_count": orders,
                "gross_revenue": round(rev, 2),
                "tax_collected": round(tax, 2),
                "average_order_value": round(rev / orders, 2)
            })
    df_rev = pd.DataFrame(rev_rows)
    
    # Inventory
    skus = [
        {"sku": "SKU-TSHIRT-01", "title": "CartCo Classic White T-Shirt"},
        {"sku": "SKU-JEANS-02", "title": "CartCo Slim Fit Blue Jeans"},
        {"sku": "SKU-HOODIE-03", "title": "CartCo Fleece Hoodie Black"},
        {"sku": "SKU-SOCKS-04", "title": "CartCo Ankle Socks (3-Pack)"},
        {"sku": "SKU-JACKET-05", "title": "CartCo Premium Denim Jacket"},
    ]
    inv_rows = []
    for s in skus:
        units = random.randint(500, 2000)
        inv_rows.append({
            "sku": s["sku"],
            "product_title": s["title"],
            "units_sold": units,
            "total_sales_amount": round(units * random.uniform(300.0, 1500.0), 2)
        })
    df_inv = pd.DataFrame(inv_rows)
    
    # Customer 360
    cust_rows = []
    domains = ["gmail.com", "yahoo.com", "outlook.com"]
    names = ["Aarav", "Dia", "Kabir", "Ira", "Reyansh", "Myra", "Vihaan", "Aanya", "Ishaan", "Sai"]
    for i in range(15):
        name = random.choice(names)
        cust_rows.append({
            "customer_id": f"LOY-{random.randint(10000, 99999)}",
            "customer_email": f"{name.lower()}{random.randint(10,99)}@{random.choice(domains)}",
            "first_purchase_date": (datetime.now() - timedelta(days=random.randint(30, 90))).strftime("%Y-%m-%d %H:%M:%S"),
            "last_purchase_date": (datetime.now() - timedelta(days=random.randint(1, 10))).strftime("%Y-%m-%d %H:%M:%S"),
            "total_orders": random.randint(1, 12),
            "total_spend": round(random.uniform(500.0, 15000.0), 2),
            "preferred_channel": random.choice(["shopify", "pos"])
        })
    df_cust = pd.DataFrame(cust_rows)
    
    return df_rev, df_inv, df_cust

# Cache the data so we don't recalculate on every endpoint load
class DataCache:
    df_rev = None
    df_inv = None
    df_cust = None
    last_load = None
    source = "mock"

def load_data():
    now = datetime.now()
    # Reload data every 5 minutes if needed, or just load once
    if DataCache.last_load and (now - DataCache.last_load).total_seconds() < 300:
        return
    
    spark = get_spark()
    if spark:
        try:
            DataCache.df_rev = spark.read.format("iceberg").load("nessie.gold.daily_revenue_channel").toPandas()
            DataCache.df_inv = spark.read.format("iceberg").load("nessie.gold.inventory_turnover").toPandas()
            DataCache.df_cust = spark.read.format("iceberg").load("nessie.gold.customer_360").toPandas()
            DataCache.source = "live"
            spark.stop()
            DataCache.last_load = now
            return
        except Exception as e:
            print(f"Failed to read from Spark/Iceberg catalog: {e}. Using mock data.")
            if spark:
                spark.stop()
    
    # Fallback to mock data
    df_rev, df_inv, df_cust = generate_mock_gold_data()
    DataCache.df_rev = df_rev
    DataCache.df_inv = df_inv
    DataCache.df_cust = df_cust
    DataCache.source = "mock"
    DataCache.last_load = now

@app.on_event("startup")
def startup_event():
    load_data()

@app.get("/api/status")
def get_status():
    load_data()
    return {"status": "ok", "source": DataCache.source, "last_load": DataCache.last_load.isoformat() if DataCache.last_load else None}

@app.get("/api/metrics")
def get_metrics():
    load_data()
    total_rev = DataCache.df_rev["gross_revenue"].sum()
    total_orders = DataCache.df_rev["order_count"].sum()
    total_tax = DataCache.df_rev["tax_collected"].sum()
    
    return {
        "total_revenue": float(total_rev),
        "total_orders": int(total_orders),
        "total_tax": float(total_tax)
    }

@app.get("/api/revenue")
def get_revenue():
    load_data()
    return DataCache.df_rev.to_dict(orient="records")

@app.get("/api/inventory")
def get_inventory():
    load_data()
    return DataCache.df_inv.to_dict(orient="records")

@app.get("/api/customers")
def get_customers():
    load_data()
    return DataCache.df_cust.to_dict(orient="records")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_dashboard():
    return FileResponse(os.path.join(static_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
