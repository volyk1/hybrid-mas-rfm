import json
import time
import os
import httpx

# Спробуємо підключити tiktoken для коректного підрахунку токенів OpenAI, якщо він є
try:
    import tiktoken
    tokenizer = tiktoken.encoding_for_model("gpt-4o") # або стандартний encoding
except ImportError:
    tokenizer = None

INPUT_FILE = "ground_truth_100.json"
OUTPUT_FILE = "results_2agents_final.json"
API_URL = "http://127.0.0.1:8000/api/chat"

def count_tokens(text):
    """Допоміжна функція для підрахунку токенів"""
    if not text:
        return 0
    if tokenizer:
        return len(tokenizer.encode(text))
    else:
        # Приблизний підрахунок, якщо tiktoken не встановлено (1 токен ~= 4 символи для англійської)
        return max(1, len(text) // 4)

def run_evaluation():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            questions = json.load(f)
    except Exception as e:
        print(f"❌ Не вдалося прочитати файл питань {INPUT_FILE}: {e}")
        return

    # 1. Завантажуємо вже існуючі результати для відновлення прогресу
    results_map = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                for item in existing_data:
                    q_id = item.get("question_id")
                    resp = item.get("mas_response", "")
                    # Засвоюємо тільки УСПІШНІ відповіді (без помилок)
                    if resp and not resp.startswith("ERROR:"):
                        results_map[q_id] = item
            print(f"🔄 Відновлено {len(results_map)} вже готових відповідей з {OUTPUT_FILE}")
        except Exception as e:
            print(f"⚠️ Не вдалося зчитати існуючий {OUTPUT_FILE}, починаємо заново: {e}")

    total = len(questions)
    print(f"🚀 Запускаємо опитування FastAPI (main.py) для {total} питань із трекінгом токенів...\n")

    with httpx.Client(timeout=600.0) as client:
        for idx, item in enumerate(questions, 1):
            q_id = item.get("question_id") or item.get("id", idx)
            q_text = item.get("question_text") or item.get("question") or item.get("text")

            # ПРОПУСКАЄМО, якщо вже є успішно порахована відповідь
            if q_id in results_map:
                print(f"[{idx}/{total}] Q{q_id} вже оброблено успішно. Пропускаємо ⏭️")
                continue

            print(f"[{idx}/{total}] Обробляємо Q{q_id}: «{q_text[:40]}...»")
            start_time = time.time()
            agent_output = ""
            
            # Змінні для токенів (якщо сервер повертає їх напряму)
            server_prompt_tokens = None
            server_completion_tokens = None

            try:
                payload = {
                    "message": q_text,
                    "session_id": f"eval_session_{q_id}"
                }

                with client.stream("POST", API_URL, json=payload) as response:
                    for line in response.iter_lines():
                        if line.startswith("data: "):
                            raw_data = line[6:]
                            try:
                                data = json.loads(raw_data)
                                
                                # Шукаємо текст відповіді
                                if data.get("type") == "final":
                                    agent_output = data.get("text", "")
                                    
                                # Якщо сервер передає токени у стрімі (наприклад, у фінальному або проміжному пакеті)
                                if "usage" in data:
                                    server_prompt_tokens = data["usage"].get("prompt_tokens")
                                    server_completion_tokens = data["usage"].get("completion_tokens")
                                elif "prompt_tokens" in data:
                                    server_prompt_tokens = data.get("prompt_tokens")
                                    server_completion_tokens = data.get("completion_tokens")
                                    
                            except Exception:
                                pass

                elapsed_time = round(time.time() - start_time, 2)
                
                if agent_output:
                    print(f"  ✅ Отримано відповідь за {elapsed_time}s")
                else:
                    agent_output = "ERROR: Empty response"
                    print(f"  ❌ Отримано порожню відповідь ({elapsed_time}s)")

            except httpx.TimeoutException:
                elapsed_time = round(time.time() - start_time, 2)
                agent_output = "ERROR: Timed out"
                print(f"  ❌ Помилка запиту: Timed out ({elapsed_time}s)")
            except Exception as e:
                elapsed_time = round(time.time() - start_time, 2)
                agent_output = f"ERROR: {str(e)}"
                print(f"  ❌ Помилка запиту: {e}")

            # Визначаємо токени: беремо з сервера, якщо вони є, інакше рахуємо програмно
            p_tokens = server_prompt_tokens if server_prompt_tokens is not None else count_tokens(q_text)
            c_tokens = server_completion_tokens if server_completion_tokens is not None else count_tokens(agent_output)
            tot_tokens = p_tokens + c_tokens

            # Записуємо новий або оновлений результат у карту разом із токенами
            results_map[q_id] = {
                "question_id": q_id,
                "question_text": q_text,
                "ground_truth": item.get("ground_truth_output", item.get("ground_truth", "")),
                "mas_response": agent_output,
                "latency_seconds": elapsed_time,
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "total_tokens": tot_tokens
            }

            print(f"  📊 Токени -> Prompt: {p_tokens} | Completion: {c_tokens} | Total: {tot_tokens}")

            # Зберігаємо відсортований список від Q1 до Q100
            sorted_results = [results_map[k] for k in sorted(results_map.keys())]
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(sorted_results, f, indent=4, ensure_ascii=False)

            time.sleep(1)

    print(f"\n🎉 Прогін повністю завершено! Результати з токенами збережено у -> {OUTPUT_FILE}")

if __name__ == "__main__":
    run_evaluation()