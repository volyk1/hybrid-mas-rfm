import sqlite3
import json
import os
import math

DB_PATH = "ecommerce_data.db"
JSON_PATH = "Segmentation.json"
TRANSACTIONS_JSON_PATH = "sales_transactions.json"

def calculate_elasticity(price, quantity):
    """Розрахунок цінової еластичності попиту: LN(Quantity) / LN(Price) (відповідно до Excel)"""
    try:
        p = float(price) if price is not None else 0.0
        q = float(quantity) if quantity is not None else 0.0
        
        # Перевірка на коректність цін і кількості (запобігаємо LN(<=1) для ціни та LN(<=0) для кількості)
        if p <= 1.0 or q <= 0:
            return 0.0
            
        ln_price = math.log(p)
        ln_quantity = math.log(q)
        
        if ln_price == 0:
            return 0.0
            
        return round(ln_quantity / ln_price, 4)
    except Exception:
        return 0.0

def create_relational_db():
    if not os.path.exists(JSON_PATH):
        print(f"Помилка: Файл {JSON_PATH} не знайдено!")
        return

    print("Зчитуємо чисті показники сегментації...")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    data = raw_data.get("data", raw_data) if isinstance(raw_data, dict) else raw_data

    print(f"Знайдено {len(data)} клієнтів. Створюємо правильную базу SQLite...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Створюємо таблицю clients з ПРАВИЛЬНИМИ типами даних (ТВІЙ НЕЗМІННИЙ КОД)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            CustomerNo INTEGER PRIMARY KEY,
            Recency INTEGER,
            Frequency INTEGER,
            Monetary REAL,
            AvgPrice REAL,
            FavMonth INTEGER,
            BoughtChristmas INTEGER,
            BoughtSet INTEGER,
            Cluster INTEGER
        )
    """)

    # Пакетна вставка даних із примусовим приведенням типів
    for item in data:
        cust_no = item.get("CustomerNo")
        if cust_no is None:
            continue
            
        cursor.execute("""
            INSERT OR REPLACE INTO clients 
            (CustomerNo, Recency, Frequency, Monetary, AvgPrice, FavMonth, BoughtChristmas, BoughtSet, Cluster)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(float(cust_no)),
            int(item.get("Recency", 0)),
            int(item.get("Frequency", 0)),
            float(item.get("Monetary", 0.0)),
            float(item.get("AvgPrice", 0.0)),
            int(item.get("FavMonth", 0)),
            int(item.get("BoughtChristmas", 0)),
            int(item.get("BoughtSet", 0)),
            int(item.get("Cluster", 0))
        ))

    # --- НОВА ТАБЛИЦЯ ТРАНЗАКЦІЙ ТА РОЗРАХУНОК ЕЛАСТИЧНОСТІ ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            TransactionNo TEXT,
            Date TEXT,
            ProductNo TEXT,
            ProductName TEXT,
            Price REAL,
            Quantity INTEGER,
            CustomerNo INTEGER,
            Country TEXT,
            Elasticity REAL,
            FOREIGN KEY (CustomerNo) REFERENCES clients (CustomerNo)
        )
    """)

    if os.path.exists(TRANSACTIONS_JSON_PATH):
        print("Зчитуємо транзакції та обчислюємо цінову еластичність попиту...")
        with open(TRANSACTIONS_JSON_PATH, "r", encoding="utf-8") as f:
            raw_tx = json.load(f)
            
        tx_data = raw_tx.get("data", raw_tx) if isinstance(raw_tx, dict) else raw_tx
        
        # Очищаємо стару таблицю транзакцій перед оновленням
        cursor.execute("DELETE FROM purchases")
        
        for tx in tx_data:
            c_no = tx.get("CustomerNo")
            if c_no is None:
                continue
                
            price = float(tx.get("Price", 0.0))
            quantity = int(tx.get("Quantity", 0))
            elasticity = calculate_elasticity(price, quantity)
            
            cursor.execute("""
                INSERT INTO purchases 
                (TransactionNo, Date, ProductNo, ProductName, Price, Quantity, CustomerNo, Country, Elasticity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(tx.get("TransactionNo", "")),
                str(tx.get("Date", "")),
                str(tx.get("ProductNo", "")),
                str(tx.get("ProductName", "")),
                price,
                quantity,
                int(float(c_no)),
                str(tx.get("Country", "")),
                elasticity
            ))
        print("✅ Покупки та розрахована цінова еластичність успішно додані в базу!")
    else:
        print(f"⚠️ Файл {TRANSACTIONS_JSON_PATH} не знайдено. Таблиця purchases залишилась порожньою.")

    conn.commit()
    conn.close()
    print(f"🎉 Базу '{DB_PATH}' успішно оновлено!")

if __name__ == "__main__":
    create_relational_db()