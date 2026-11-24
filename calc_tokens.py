import json
import os

# Спробуємо використати tiktoken для максимальної точності, якщо він є
try:
    import tiktoken
    tokenizer = tiktoken.encoding_for_model("gpt-4o")
except ImportError:
    tokenizer = None

TARGET_FILE = "results_2agents_final.json"

def count_tokens(text):
    """Точний або резервний підрахунок токенів"""
    if not text:
        return 0
    if tokenizer:
        return len(tokenizer.encode(text))
    else:
        # Резервний метод приблизного підрахунку (1 токен ~= 4 символи)
        return max(1, len(text) // 4)

def update_file_with_tokens():
    if not os.path.exists(TARGET_FILE):
        print(f"❌ Файл {TARGET_FILE} не знайдено в поточній папці!")
        return

    try:
        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Помилка читання файлу {TARGET_FILE}: {e}")
        return

    print(f"🚀 Запускаємо підрахунок токенів для {len(data)} записів у файлі {TARGET_FILE}...\n")

    updated_count = 0
    for idx, item in enumerate(data, 1):
        q_text = item.get("question_text", "")
        mas_resp = item.get("mas_response", "")

        # Рахуємо токени
        p_tokens = count_tokens(q_text)
        c_tokens = count_tokens(mas_resp)
        tot_tokens = p_tokens + c_tokens

        # Додаємо поля у словник запису
        item["prompt_tokens"] = p_tokens
        item["completion_tokens"] = c_tokens
        item["total_tokens"] = tot_tokens

        q_id = item.get("question_id", idx)
        print(f"[{idx}/{len(data)}] Q{q_id} -> Prompt: {p_tokens} | Completion: {c_tokens} | Total: {tot_tokens}")
        updated_count += 1

    # Зберігаємо оновлені дані назад у той самий файл
    try:
        with open(TARGET_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"\n🎉 Успішно оновлено {updated_count} записів! Збережено у -> {TARGET_FILE}")
    except Exception as e:
        print(f"❌ Помилка запису файлу {TARGET_FILE}: {e}")

if __name__ == "__main__":
    update_file_with_tokens()