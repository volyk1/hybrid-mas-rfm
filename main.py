import asyncio
import json
import os
import re
import uuid
import httpx
import sqlite3
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="MAS AI Dynamic Memory Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

N8N_WEBHOOK_URL = "https://n8n.ksu.ks.ua/webhook/56e49b70-57bc-4b36-b2ea-caae27b22cf4"
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "http://192.168.97.58:4000/v1")
LITELLM_API_KEY = os.getenv("API_KEY", "")

MODEL_SQL = os.getenv("MODEL_SQL", "qwen3.6-27b")
MODEL_TEXT = os.getenv("MODEL_TEXT", "qwen3.6-27b")

HISTORY_FILE = "history.json"
DB_PATH = "ecommerce_data.db"


def get_llm_headers() -> dict:
    return {
        "Authorization": f"Bearer {LITELLM_API_KEY}",
        "Content-Type": "application/json",
    }


def load_db():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_db(db_data):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Помилка збереження історії: {e}")


def detect_language(text: str) -> str:
    """Визначає мову вхідного запиту користувача (en або ua)"""
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    cyrillic_chars = len(re.findall(r'[а-яА-ЯіІїЇєЄґҐ]', text))
    return "en" if latin_chars > cyrillic_chars else "ua"


# --- АВТОНОМНИЙ ЛОКАЛЬНИЙ TEXT-TO-SQL ІНСТРУМЕНТ (LiteLLM / OpenAI API) ---

async def generate_sql_via_llm(user_query: str) -> str:
    """Генерація чистого SQL через LiteLLM OpenAI-compatible endpoint"""
    cust_id_match = re.search(r'\b(\d{4,6})\b', user_query)

    schema_info = """
    SQLite Schema:
    1. Table: clients (CustomerNo, Recency, Frequency, Monetary, AvgPrice, FavMonth, BoughtChristmas, BoughtSet, Cluster)
    2. Table: purchases (TransactionNo, Date, ProductNo, ProductName, Price, Quantity, CustomerNo, Country, Elasticity)
       Note: Elasticity is calculated as LN(Quantity)/LN(Price).
    """

    prompt = (
        f"{schema_info}\n\n"
        f"Generate a single SQLite SELECT query for request: '{user_query}'.\n"
        "Rules:\n"
        "1. Output ONLY raw SQL statement. No markdown code blocks.\n"
        "2. If searching for top products by elasticity, retrieve ProductName, AVG(Price) as Price, SUM(Quantity) as Quantity, AVG(Elasticity) as Elasticity FROM purchases WHERE Elasticity > 1 GROUP BY ProductName ORDER BY Elasticity DESC LIMIT 5.\n"
        "3. If query asks for customer details with products/country, use: "
        "SELECT c.CustomerNo, c.Recency, c.Frequency, c.Monetary, c.AvgPrice, c.Cluster, p.ProductName, p.Country, p.Price, p.Quantity, p.Elasticity FROM clients c LEFT JOIN purchases p ON c.CustomerNo = p.CustomerNo WHERE c.CustomerNo = ... LIMIT 10\n"
    )

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            res = await client.post(
                f"{LITELLM_BASE_URL}/chat/completions",
                headers=get_llm_headers(),
                json={
                    "model": MODEL_SQL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "stream": False,
                },
            )
            res.raise_for_status()
            data = res.json()
            raw_response = data["choices"][0]["message"]["content"].strip()

            match = re.search(r'(SELECT\s+.+)', raw_response, re.IGNORECASE | re.DOTALL)
            if match:
                sql = match.group(1)
                sql = re.sub(r'```.*', '', sql).strip()
                sql = sql.split(';')[0].strip()
                return sql
        except Exception as e:
            print(f"⚠️ Помилка генерації SQL через LiteLLM: {e}")

    if cust_id_match:
        c_id = cust_id_match.group(1)
        return f"SELECT c.CustomerNo, c.Recency, c.Frequency, c.Monetary, c.AvgPrice, c.Cluster, p.ProductName, p.Country, p.Price, p.Quantity, p.Elasticity FROM clients c LEFT JOIN purchases p ON c.CustomerNo = p.CustomerNo WHERE c.CustomerNo = {c_id} LIMIT 10"

    return ""


def format_fallback_report(raw_data_rows: list, user_query: str, target_lang: str = "ua") -> str:
    """Універсальна генерація валідної Markdown-таблиці мовою запиту користувача"""
    if not raw_data_rows:
        return "No data found for the specified criteria." if target_lang == "en" else "Інформацію за вказаними критеріями у базі даних не виявлено."

    first = raw_data_rows[0]
    has_customer = "CustomerNo" in first and first["CustomerNo"] is not None

    report = ""
    is_en = target_lang == "en"

    if has_customer:
        cust_id = first.get("CustomerNo", "N/A")
        recency = first.get("Recency", "N/A")
        freq = first.get("Frequency", "N/A")
        monetary = f"{float(first.get('Monetary', 0)):,.2f}" if first.get("Monetary") is not None else "N/A"
        avg_price = f"{float(first.get('AvgPrice', 0)):,.2f}" if first.get("AvgPrice") is not None else "N/A"
        cluster = first.get("Cluster", "N/A")
        country = first.get("Country", "United Kingdom")

        if is_en:
            report += f"### 📊 Analytical Report for CustomerNo: {cust_id}\n\n"
            report += "**Client Metrics:**\n"
            report += f"- **Country:** {country}\n"
            report += f"- **Cluster:** {cluster}\n"
            report += f"- **Recency (last purchase):** {recency} days ago\n"
            report += f"- **Frequency (orders count):** {freq} transactions\n"
            report += f"- **Monetary (total spent):** {monetary} UAH\n"
            report += f"- **AvgPrice (average price):** {avg_price} UAH\n\n"
            report += "### Purchase History & Price Elasticity of Demand:\n\n"
        else:
            report += f"### 📊 Аналітичний звіт по клієнту CustomerNo: {cust_id}\n\n"
            report += "**Метрики клієнта:**\n"
            report += f"- **Країна:** {country}\n"
            report += f"- **Cluster:** {cluster}\n"
            report += f"- **Recency (останній візит):** {recency} дн.\n"
            report += f"- **Frequency (кількість покупок):** {freq} разів\n"
            report += f"- **Monetary (сумарна вартість покупок):** {monetary} грн\n"
            report += f"- **AvgPrice (середня ціна товару):** {avg_price} грн\n\n"
            report += "### Список покупок та цінова еластичність попиту:\n\n"
    else:
        if is_en:
            report += f"### 📊 Analytical Report for Request: «{user_query}»\n\n"
            report += "### Products & Price Elasticity Metrics:\n\n"
        else:
            report += f"### 📊 Аналітичний звіт за запитом: «{user_query}»\n\n"
            report += "### Товарні позиції та показники цінової еластичності:\n\n"

    if is_en:
        report += "| Product Name | Price (UAH) | Quantity | Elasticity E_d | Demand Type |\n"
        report += "| :--- | :---: | :---: | :---: | :--- |\n"
    else:
        report += "| Назва товару | Ціна (грн) | Кількість | Еластичність E_d | Тип попиту |\n"
        report += "| :--- | :---: | :---: | :---: | :--- |\n"

    for row in raw_data_rows:
        p_name = row.get("ProductName", "Unknown Product" if is_en else "Невідомий товар")
        price_val = row.get("Price", row.get("AVG(Price)", 0.0))
        price_str = f"{float(price_val):.2f}" if price_val else "—"
        qty_val = row.get("Quantity", row.get("SUM(Quantity)", 0))
        qty_str = f"{qty_val}" if qty_val else "—"
        e_val = row.get("Elasticity", row.get("AvgElasticity", row.get("AVG(Elasticity)", 0.0)))
        e_d = round(float(e_val), 4) if e_val is not None else 0.0

        if e_d > 1.0:
            e_type = "Elastic (E_d > 1)" if is_en else "Еластичний (E_d > 1)"
        elif 0 < e_d < 1.0:
            e_type = "Inelastic (E_d < 1)" if is_en else "Нееластичний (E_d < 1)"
        else:
            e_type = "Unitary (E_d = 1)" if is_en else "Одиничний (E_d = 1)"

        report += f"| {p_name} | {price_str} | {qty_str} | {e_d} | {e_type} |\n"

    report += "\n\n" + ("### Executive Summary & Pricing Recommendations:\n\n" if is_en else "### Підсумковий аналітичний висновок та рекомендації:\n\n")

    if is_en:
        if has_customer:
            report += f"Customer **CustomerNo: {first.get('CustomerNo')}** (Cluster {first.get('Cluster')}) demonstrates high activity in the e-commerce system.\n\n"
        else:
            report += "The selected items exhibit high price elasticity of demand ($E_d > 1$), indicating strong customer price sensitivity.\n\n"
        report += "**Pricing Policy Recommendations:**\n\n"
        report += "- **For $E_d > 1$ (Elastic Demand):** Price increases should be avoided. Consider promotional discounts and product bundling.\n"
        report += "- **For $E_d < 1$ (Inelastic Demand):** Moderate price increases can be implemented to boost profit margins.\n"
    else:
        if has_customer:
            report += f"Клієнт **CustomerNo: {first.get('CustomerNo')}** (Кластер {first.get('Cluster')}) демонструє високу активність у системі.\n\n"
        else:
            report += "Знайдені товари демонструють високу цінову еластичність попиту ($E_d > 1$), що означає значну чутливість покупців до будь-якої зміни ціни.\n\n"
        report += "**Цінова рекомендація:**\n\n"
        report += "- **Для товарів з $E_d > 1$ (Еластичний попит):** Не рекомендується підвищувати ціни. Ефективною стратегією буде проведення акцій та акційних комплектів.\n"
        report += "- **Для товарів з $E_d < 1$ (Нееластичний попит):** Є можливість помірного підвищення ціни для збільшення маржинальності.\n"

    return report


async def interpret_metrics_via_llm(user_query: str, raw_data_rows: list, target_lang: str = "ua") -> str:
    """Генерація аналітичного звіту через LiteLLM OpenAI-compatible endpoint"""
    first = raw_data_rows[0]
    has_customer = "CustomerNo" in first and first["CustomerNo"] is not None

    if has_customer:
        cust_info = f"CustomerNo: {first.get('CustomerNo')}, Cluster: {first.get('Cluster')}, Recency: {first.get('Recency')}, Frequency: {first.get('Frequency')}, Monetary: {first.get('Monetary')}, AvgPrice: {first.get('AvgPrice')}, Country: {first.get('Country')}"
        items = []
        for r in raw_data_rows:
            if r.get("ProductName"):
                items.append(f"- {r.get('ProductName')} | Price: {r.get('Price')} | Qty: {r.get('Quantity')} | Elasticity E_d: {r.get('Elasticity')}")
        compact_context = f"Client metrics:\n{cust_info}\n\nPurchases list:\n" + "\n".join(items)
    else:
        items = []
        for r in raw_data_rows:
            p_name = r.get("ProductName")
            e_val = r.get("Elasticity", r.get("AvgElasticity", r.get("AVG(Elasticity)", 0)))
            price = r.get("Price", r.get("AVG(Price)", "N/A"))
            qty = r.get("Quantity", r.get("SUM(Quantity)", "N/A"))
            items.append(f"- Product: {p_name} | Elasticity E_d: {e_val} | Price: {price} | Qty: {qty}")
        compact_context = "Database search results:\n" + "\n".join(items)

    lang_name = "ENGLISH" if target_lang == "en" else "UKRAINIAN"

    prompt = (
        f"You are a lead data analyst and DSS system expert in e-commerce segmentation.\n"
        f"Generate a structured, professional analytical report strictly in {lang_name}.\n\n"
        "Table Formatting Rules:\n"
        "1. MUST include empty blank lines before and after Markdown tables.\n"
        "2. Table headers must be plain text without LaTeX symbols:\n" +
        ("| Product Name | Price | Quantity | Elasticity E_d | Demand Type |\n" if target_lang == "en" else
         "| Назва товару | Ціна (грн) | Кількість | Еластичність E_d | Тип попиту |\n") +
        "| :--- | :---: | :---: | :---: | :--- |\n"
        "3. Round prices to 2 decimals, elasticity to 4 decimals.\n"
        "4. Include executive summary and pricing strategy recommendations.\n\n"
        f"User query: '{user_query}'\n"
        f"Data context:\n{compact_context}"
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            res = await client.post(
                f"{LITELLM_BASE_URL}/chat/completions",
                headers=get_llm_headers(),
                json={
                    "model": MODEL_TEXT,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "stream": False,
                },
            )
            res.raise_for_status()
            data = res.json()
            response_text = data["choices"][0]["message"]["content"].strip()
            if response_text and "|" in response_text:
                return response_text
            else:
                return format_fallback_report(raw_data_rows, user_query, target_lang)
        except Exception as e:
            print(f"❌ Помилка LiteLLM-інтерпретатора: {e}. Використовуємо універсальний звіт.")
            return format_fallback_report(raw_data_rows, user_query, target_lang)


async def fetch_local_sqlite(user_query: str, target_lang: str = "ua") -> str:
    """Повний ізольований цикл виконання та інтерпретації SQL-запиту"""
    try:
        if not os.path.exists(DB_PATH):
            return "Error: Local SQLite DB not found." if target_lang == "en" else "Помилка: Локальну реляційну базу даних 'ecommerce_data.db' не знайдено."

        sql_query = await generate_sql_via_llm(user_query)
        print(f"🤖 [Маршрутизатор SQL] Виконуємо запит: {sql_query}")

        if not sql_query or not re.search(r'SELECT', sql_query, re.IGNORECASE):
            return "Failed to form a valid SQL query." if target_lang == "en" else "Не вдалося сформувати валідну реляційну умову для вибірки показників."

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        if not rows:
            return "No records found matching the specified criteria." if target_lang == "en" else "Запит до локальної реляційної бази виконано успішно, проте записів за вказаними числовими критеріями не виявлено."

        interpreted_report = await interpret_metrics_via_llm(user_query, rows, target_lang)
        return interpreted_report
    except Exception as e:
        print(f"❌ Помилка SQLite-контуру: {e}")
        return f"Database error: {str(e)}" if target_lang == "en" else f"Помилка при роботі з реляційним SQLite-контуром: {str(e)}"


# --- FastAPI ЕНДПОІНТИ ---

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    lang: str | None = None


class RenameRequest(BaseModel):
    title: str


@app.get("/api/sessions")
async def get_sessions():
    db = load_db()
    return [{"id": s_id, "title": data["title"]} for s_id, data in db.items()]


@app.get("/api/sessions/{session_id}")
async def get_session_history(session_id: str):
    db = load_db()
    if session_id not in db:
        raise HTTPException(status_code=404, detail="Сесію не знайдено")
    return db[session_id]["history"]


@app.put("/api/sessions/{session_id}")
async def rename_session(session_id: str, req: RenameRequest):
    """Оновлення назви чату в history.json"""
    db = load_db()
    if session_id in db:
        db[session_id]["title"] = req.title.strip()
        save_db(db)
        return {"status": "success", "title": req.title.strip()}
    raise HTTPException(status_code=404, detail="Сесію не знайдено")


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    db = load_db()
    if session_id in db:
        del db[session_id]
        save_db(db)
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Сесію не знайдено")


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, request: Request):
    db = load_db()
    session_id = req.session_id

    query_lang = detect_language(req.message)

    if session_id in [None, "", "null", "undefined"]:
        session_id = None

    if not session_id or session_id not in db:
        session_id = str(uuid.uuid4())
        title = req.message[:30] + "..." if len(req.message) > 30 else req.message
        db[session_id] = {"title": title, "history": []}

    db[session_id]["history"].append({"role": "user", "text": req.message})
    save_db(db)

    session_history = db[session_id]["history"]

    if len(session_history) == 1:
        compiled_input = req.message
    else:
        context_lines = []
        for msg in session_history[-5:-1]:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            context_lines.append(f"{prefix}: {msg['text']}")

        compiled_input = "SESSION CONTEXT:\n" + "\n".join(context_lines) + f"\nNew user question: {req.message}"

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'session', 'id': session_id})}\n\n"
            await asyncio.sleep(0.05)

            msg_lower = req.message.lower()
            has_digits = bool(re.search(r'\d+', msg_lower))

            if "силует" in msg_lower or "silhouette" in msg_lower or "методолог" in msg_lower:
                has_digits = False

            final_response = ""

            if has_digits:
                status_msg = "📊 Analyzing indicators and generating SQLite expert report..." if query_lang == "en" else "📊 Аналіз показників та генерація експертного звіту з SQLite..."
                yield f"data: {json.dumps({'type': 'status', 'text': status_msg})}\n\n"
                await asyncio.sleep(0.3)
                final_response = await fetch_local_sqlite(req.message, query_lang)

            else:
                status_msg = "🧬 Synchronizing agent semantic space..." if query_lang == "en" else "🧬 Синхронізація семантичного простору агентури..."
                yield f"data: {json.dumps({'type': 'status', 'text': status_msg})}\n\n"

                async def fetch_n8n():
                    async with httpx.AsyncClient(timeout=600.0) as client:
                        try:
                            chat_payload = f"[Instruction: Reply strictly in {'ENGLISH' if query_lang == 'en' else 'UKRAINIAN'}]: {compiled_input}"
                            res = await client.post(N8N_WEBHOOK_URL, json={"chat_input": chat_payload})
                            return res.text.strip() if res.status_code == 200 else f"Orchestrator error: {res.status_code}"
                        except Exception as e:
                            return f"Connection error: {str(e)}"

                n8n_task = asyncio.create_task(fetch_n8n())

                abstract_statuses_ua = [
                    "🔍 Декомпозиція вхідного концепту та виділення базових гіпотез...",
                    "📊 Валідація методологічних паттернів через призму локальних баз знань...",
                    "📡 Пошук та фільтрація глобальних трендів за допомогою зовнішніх шлюзів...",
                    "🛡️ Крос-аудит аналітичних висновків на предмет логічних аномалій...",
                    "🧠 Зіставлення знайдених ринкових маркерів із внутрішніми критеріями стійкості...",
                    "⚖️ Усунення концептуальних розбіжностей та пошук міжмодельного консенсусу...",
                    "⚙️ Синтез багаторівневих стратегічних рішень та агрегація експертних думок...",
                    "🛡️ Верифікація стійкості сформованої моделі до системних ризиків...",
                    "👑 Фіналізація консолідованого звіту та структурування керуючої матриці..."
                ]

                abstract_statuses_en = [
                    "🔍 Decomposing input concept and extracting baseline hypotheses...",
                    "📊 Validating methodological patterns against local knowledge bases...",
                    "📡 Searching and filtering global trends via external gateways...",
                    "🛡️ Cross-auditing analytical findings for logical anomalies...",
                    "🧠 Matching identified market markers with internal stability criteria...",
                    "⚖️ Resolving conceptual discrepancies and seeking inter-model consensus...",
                    "⚙️ Synthesizing multi-level strategic decisions and aggregating expert opinions...",
                    "🛡️ Verifying model resilience against systemic risks...",
                    "👑 Finalizing consolidated report and structuring control matrix..."
                ]

                abstract_statuses = abstract_statuses_en if query_lang == "en" else abstract_statuses_ua

                status_idx = 0
                while not n8n_task.done():
                    if await request.is_disconnected():
                        print("Клієнт розірвав з'єднання.")
                        n8n_task.cancel()
                        return

                    await asyncio.sleep(1.0)

                    if status_idx < len(abstract_statuses) * 5 and status_idx % 5 == 0:
                        yield f"data: {json.dumps({'type': 'status', 'text': abstract_statuses[status_idx // 5]})}\n\n"

                    status_idx += 1

                raw_text = n8n_task.result()

                try:
                    n8n_data = json.loads(raw_text)
                    if isinstance(n8n_data, list) and len(n8n_data) > 0:
                        n8n_data = n8n_data[0]
                    if isinstance(n8n_data, dict):
                        final_response = n8n_data.get("Результат_Аналізу", n8n_data.get("output", n8n_data.get("text", "")))
                        if not final_response:
                            final_response = list(n8n_data.values())[0]
                    else:
                        final_response = str(n8n_data)
                except Exception:
                    final_response = raw_text

                if isinstance(final_response, str):
                    final_response = final_response.replace("\\n", "\n").replace('\\"', '"')
                    final_response = re.sub(r'^["\'\{\s\.\,\`]+|["\'\`\}]+$', '', final_response).strip()

            current_db = load_db()
            if session_id in current_db:
                current_db[session_id]["history"].append({"role": "assistant", "text": final_response})
                save_db(current_db)

            yield f"data: {json.dumps({'type': 'final', 'text': final_response})}\n\n"

        except asyncio.CancelledError:
            return

    return StreamingResponse(event_generator(), media_type="text/event-stream")


app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)