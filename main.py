import os
import sqlite3
import json
from datetime import datetime, date
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

DB_PATH = os.path.join(os.path.dirname(__file__), "pantry.db")

app = FastAPI(title="Smart Pantry & Expiry Manager", version="1.0.0")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL, -- Fridge, Freezer, Pantry, Spice Rack
            quantity REAL NOT NULL DEFAULT 1.0,
            unit TEXT NOT NULL DEFAULT 'шт',
            expiry_date TEXT NOT NULL, -- YYYY-MM-DD
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shopping_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            quantity TEXT NOT NULL DEFAULT '1',
            is_bought INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            ingredients_json TEXT NOT NULL, -- list of strings
            instructions TEXT NOT NULL
        )
    """)

    # Seed initial pantry products and recipes if empty
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        today = date.today()
        prods = [
            ("Молоко 3.2%", "Fridge", 1.0, "л", (today.fromordinal(today.toordinal() + 2)).isoformat()), # Expiring in 2 days
            ("Творог фермерский", "Fridge", 400, "г", (today.fromordinal(today.toordinal() - 1)).isoformat()), # Expired yesterday
            ("Куриное филе", "Freezer", 1.2, "кг", (today.fromordinal(today.toordinal() + 60)).isoformat()),
            ("Яйца С0", "Fridge", 10, "шт", (today.fromordinal(today.toordinal() + 14)).isoformat()),
            ("Рис Басмати", "Pantry", 2.0, "кг", (today.fromordinal(today.toordinal() + 180)).isoformat()),
            ("Морковь", "Fridge", 1.0, "кг", (today.fromordinal(today.toordinal() + 8)).isoformat()),
            ("Лук репчатый", "Pantry", 2.5, "кг", (today.fromordinal(today.toordinal() + 25)).isoformat()),
            ("Сыр Пармезан", "Fridge", 200, "г", (today.fromordinal(today.toordinal() + 18)).isoformat()),
            ("Спагетти", "Pantry", 500, "г", (today.fromordinal(today.toordinal() + 240)).isoformat()),
            ("Зира и специи для плова", "Spice Rack", 100, "г", (today.fromordinal(today.toordinal() + 365)).isoformat())
        ]
        cursor.executemany("INSERT INTO products (name, location, quantity, unit, expiry_date) VALUES (?, ?, ?, ?, ?)", prods)

        recipes = [
            ("Плов Узбекский домашний", "Горячее", json.dumps(["Рис Басмати", "Морковь", "Лук репчатый", "Куриное филе", "Зира и специи для плова"]), "Обжарить лук и мясо в казане, добавить морковь (зирвак), засыпать промытый рис и варить до готовности."),
            ("Паста Карбонара", "Паста", json.dumps(["Спагетти", "Яйца С0", "Сыр Пармезан"]), "Отварить спагетти al dente, смешать желтки с тертым сыром и соединить на горячей сковороде."),
            ("Сырники домашние", "Завтрак", json.dumps(["Творог фермерский", "Яйца С0"]), "Размять творог с яйцом, сформировать шайбы и обжарить на сковороде до золотистой корочки."),
            ("Омлет с сыром", "Завтрак", json.dumps(["Яйца С0", "Молоко 3.2%", "Сыр Пармезан"]), "Взбить яйца с молоком, вылить на сковороду и посыпать сыром.")
        ]
        cursor.executemany("INSERT INTO recipes (name, category, ingredients_json, instructions) VALUES (?, ?, ?, ?)", recipes)

    conn.commit()
    conn.close()

init_db()

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2)
    location: str
    quantity: float = 1.0
    unit: str = "шт"
    expiry_date: str # YYYY-MM-DD

class ShoppingItemCreate(BaseModel):
    item_name: str
    quantity: str = "1"

@app.get("/api/products")
def get_products(location: Optional[str] = None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    if location and location != "ALL":
        sql += " AND location = ?"
        params.append(location)

    sql += " ORDER BY expiry_date ASC"
    cursor.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    today = date.today()
    for p in rows:
        try:
            exp = datetime.strptime(p["expiry_date"], "%Y-%m-%d").date()
            days_left = (exp - today).days
            p["days_left"] = days_left
            if days_left < 0:
                p["status"] = "EXPIRED"
            elif days_left <= 3:
                p["status"] = "EXPIRING_SOON"
            else:
                p["status"] = "FRESH"
        except Exception:
            p["days_left"] = 999
            p["status"] = "FRESH"

    return {"products": rows}

@app.post("/api/products")
def add_product(prod: ProductCreate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (name, location, quantity, unit, expiry_date)
        VALUES (?, ?, ?, ?, ?)
    """, (prod.name.strip(), prod.location, prod.quantity, prod.unit, prod.expiry_date))
    pid = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "created", "id": pid}

@app.delete("/api/products/{prod_id}")
def delete_product(prod_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@app.get("/api/shopping")
def get_shopping_list():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shopping_list ORDER BY is_bought ASC, id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"items": rows}

@app.post("/api/shopping")
def add_shopping_item(item: ShoppingItemCreate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO shopping_list (item_name, quantity)
        VALUES (?, ?)
    """, (item.item_name.strip(), item.quantity))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "created", "id": new_id}

@app.post("/api/shopping/sync-expiring")
def sync_expiring_to_shopping():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today_str = date.today().isoformat()

    # Find products expiring <= 3 days
    cursor.execute("""
        SELECT name, quantity, unit FROM products 
        WHERE julianday(expiry_date) - julianday('now') <= 3.0
    """)
    rows = cursor.fetchall()

    added = 0
    for name, qty, unit in rows:
        cursor.execute("SELECT id FROM shopping_list WHERE item_name = ? AND is_bought = 0", (name,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO shopping_list (item_name, quantity) VALUES (?, ?)", (name, f"{qty} {unit}"))
            added += 1

    conn.commit()
    conn.close()
    return {"status": "synced", "added_count": added}

@app.put("/api/shopping/{item_id}/toggle")
def toggle_shopping_item(item_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE shopping_list SET is_bought = 1 - is_bought WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "toggled"}

@app.delete("/api/shopping/{item_id}")
def delete_shopping_item(item_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shopping_list WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@app.get("/api/recipes/suggestions")
def get_recipe_suggestions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM products WHERE julianday(expiry_date) >= julianday('now') - 2.0")
    available_products = {r[0].lower().strip() for r in cursor.fetchall()}

    cursor.execute("SELECT * FROM recipes")
    recipes_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    suggestions = []
    for rec in recipes_rows:
        req_ingredients = json.loads(rec["ingredients_json"])
        matched = []
        missing = []

        for ing in req_ingredients:
            # check substring match
            found = False
            for avail in available_products:
                if avail in ing.lower() or ing.lower() in avail:
                    found = True
                    break
            if found:
                matched.append(ing)
            else:
                missing.append(ing)

        total = len(req_ingredients)
        pct = round((len(matched) / total) * 100) if total > 0 else 0

        suggestions.append({
            "id": rec["id"],
            "name": rec["name"],
            "category": rec["category"],
            "match_pct": pct,
            "matched_ingredients": matched,
            "missing_ingredients": missing,
            "instructions": rec["instructions"]
        })

    suggestions.sort(key=lambda x: x["match_pct"], reverse=True)
    return {"suggestions": suggestions}

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_dir, "index.html"))
