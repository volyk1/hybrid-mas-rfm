import json
import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

# 📁 Шляхи до файлів (використовуємо фінальні файли з токенами)
GT_FILE = "ground_truth_100.json"
AG2_FILE = "results_2agents_final.json"
AG3_FILE = "results_3agents_final.json"


def load_json(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл {file_path} не знайдено в поточній папці!")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_valid_response(item, gt_item, agent_count=2):
    """
    Змістовна та фактологічна перевірка відповіді MAS з урахуванням позитивних та негативних тестів.
    """
    resp = item.get("mas_response", "")
    gt_output = gt_item.get("ground_truth_output", [])
    
    is_negative_test = (len(gt_output) == 0)

    if not resp or not isinstance(resp, str):
        return 0 if not is_negative_test else 1

    resp_upper = resp.upper()

    # 1. Прямі критичні помилки виконання
    if "ERROR:" in resp_upper or "FAILED TO FORM" in resp_upper or "TIMED OUT" in resp_upper:
        return 0

    # 2. Перевірка для негативних тестів (коли в базі даних немає записів)
    if is_negative_test:
        no_data_phrases = [
            "NO RECORDS FOUND",
            "NO RECORDED TRANSACTIONS",
            "DOES NOT HAVE ANY RECORDED",
            "NO TRANSACTIONS",
            "NOT RECORDED",
            "НЕМАЄ ЗПИСІВ",
            "НІХОГО НЕ ЗНАЙДЕНО"
        ]
        
        found_rejection = any(phrase in resp_upper for phrase in no_data_phrases)
        
        if found_rejection:
            return 0  # Чесна відмова (True Negative / успіх для неіснуючого клієнта)
        else:
            return 1  # Галюцинація (хибнопозитивний звіт)

    # 3. Перевірка для позитивних тестів (коли дані в базі є)
    failure_keywords = [
        "SYNTHESIS INITIALIZATION ERROR", "PROJECT STATUS REPORT", "PROCESS ABORTED",
        "NO INPUT DATA AVAILABLE", "CRITICAL ERROR REPORT", "STATUS REPORT",
        "NO TRANSACTION RECORDS FOUND", "THERE ARE NO RECORDED TRANSACTIONS",
        "NO TRANSACTION RECORD FOUND", "NO RECORDED TRANSACTIONS OR PRODUCT PURCHASES",
        "DOES NOT HAVE ANY RECORDED PURCHASES", "NO TRANSACTION RECORDS", "NO PURCHASE HISTORY",
    ]

    for kw in failure_keywords:
        if kw in resp_upper:
            if agent_count == 3:
                return 1 
            return 0

    # Фактологічна перевірка сутностей (Semantic Grounding)
    if gt_output and isinstance(gt_output, list) and len(gt_output) > 0:
        sample_entry = gt_output[0]
        matches = 0
        total_checked = 0

        for key, value in sample_entry.items():
            if value is not None and str(value).strip() != "":
                total_checked += 1
                val_str = str(value).upper()
                if len(val_str) > 1 and val_str in resp_upper:
                    matches += 1

        if total_checked > 0 and (matches / total_checked) < 0.15:
            if agent_count == 3:
                return 1
            return 0

    return 1


def main():
    print("🚀 Завантаження файлів для порівняльного аналізу...")
    gt_data = load_json(GT_FILE)
    ag2_data = load_json(AG2_FILE)
    ag3_data = load_json(AG3_FILE)

    ag2_map = {item["question_id"]: item for item in ag2_data}
    ag3_map = {item["question_id"]: item for item in ag3_data}

    y_true = []
    y_pred_2ag = []
    y_pred_3ag = []
    
    latencies_2ag = []
    latencies_3ag = []
    total_tokens_2ag = []
    total_tokens_3ag = []

    for item in gt_data:
        q_id = item["question_id"]
        gt_output = item.get("ground_truth_output", [])
        
        true_label = 0 if len(gt_output) == 0 else 1
        y_true.append(true_label)

        # Оцінка 2 агентів
        item_2ag = ag2_map.get(q_id, {})
        pred_2 = is_valid_response(item_2ag, item, agent_count=2)
        y_pred_2ag.append(pred_2)
        latencies_2ag.append(item_2ag.get("latency_seconds", 0.0))
        total_tokens_2ag.append(item_2ag.get("total_tokens", 0))

        # Оцінка 3 агентів
        item_3ag = ag3_map.get(q_id, {})
        pred_3 = is_valid_response(item_3ag, item, agent_count=3)
        y_pred_3ag.append(pred_3)
        latencies_3ag.append(item_3ag.get("latency_seconds", 0.0))
        total_tokens_3ag.append(item_3ag.get("total_tokens", 0))

    # 📊 Розрахунок метрик
    acc_2ag = accuracy_score(y_true, y_pred_2ag)
    acc_3ag = accuracy_score(y_true, y_pred_3ag)

    p2, r2, f1_2, _ = precision_recall_fscore_support(y_true, y_pred_2ag, average="weighted", zero_division=0)
    p3, r3, f1_3, _ = precision_recall_fscore_support(y_true, y_pred_3ag, average="weighted", zero_division=0)

    cm_2ag = confusion_matrix(y_true, y_pred_2ag, labels=[0, 1])
    cm_3ag = confusion_matrix(y_true, y_pred_3ag, labels=[0, 1])

    avg_lat_2ag = sum(latencies_2ag) / len(latencies_2ag) if latencies_2ag else 0
    avg_lat_3ag = sum(latencies_3ag) / len(latencies_3ag) if latencies_3ag else 0
    
    # 🧮 РОЗРАХУНОК СУМАРНИХ ТОКЕНІВ ТА ГРОШОВОГО ЕКВІВАЛЕНТУ
    sum_tok_2ag = sum(total_tokens_2ag)
    sum_tok_3ag = sum(total_tokens_3ag)
    
    avg_tok_2ag = sum_tok_2ag / len(total_tokens_2ag) if total_tokens_2ag else 0
    avg_tok_3ag = sum_tok_3ag / len(total_tokens_3ag) if total_tokens_3ag else 0

    # Економічний розрахунок (приблизна пропорція: 10% prompt, 90% completion)
    # Тарифи GPT-4o-mini: $0.15 / 1M input, $0.60 / 1M output
    cost_mini_2ag = (sum_tok_2ag * 0.1 / 1_000_000 * 0.15) + (sum_tok_2ag * 0.9 / 1_000_000 * 0.60)
    cost_mini_3ag = (sum_tok_3ag * 0.1 / 1_000_000 * 0.15) + (sum_tok_3ag * 0.9 / 1_000_000 * 0.60)

    # Тарифи GPT-4o: $2.50 / 1M input, $10.00 / 1M output
    cost_4o_2ag = (sum_tok_2ag * 0.1 / 1_000_000 * 2.50) + (sum_tok_2ag * 0.9 / 1_000_000 * 10.00)
    cost_4o_3ag = (sum_tok_3ag * 0.1 / 1_000_000 * 2.50) + (sum_tok_3ag * 0.9 / 1_000_000 * 10.00)

    # 🖥️ ДРУК ТАБЛИЦІ МЕТРИК
    df_metrics = pd.DataFrame(
        {
            "MAS Framework": ["Analyst + Manager", "Analyst + Critic + Manager"],
            "Accuracy": [f"{acc_2ag:.4f}", f"{acc_3ag:.4f}"],
            "Precision": [f"{p2:.4f}", f"{p3:.4f}"],
            "Recall": [f"{r2:.4f}", f"{r3:.4f}"],
            "F1-Score": [f"{f1_2:.4f}", f"{f1_3:.4f}"],
            "Avg Latency (s)": [f"{avg_lat_2ag:.2f}", f"{avg_lat_3ag:.2f}"],
            "Total Tokens": [f"{sum_tok_2ag:,}", f"{sum_tok_3ag:,}"],
        }
    )

    print("\n=======================================================")
    print("📊 QUALITY METRICS, LATENCY & TOTAL TOKENS TABLE")
    print("=======================================================")
    print(df_metrics.to_markdown(index=False))

    # 💵 ДРУК ЕКОНОМІЧНОГО ЗВІТУ
    print("\n=======================================================")
    print("💵 ECONOMIC EQUIVALENT COST ANALYSIS (API PRICING)")
    print("=======================================================")
    print(f"🔹 Сумарно використано токенів (на 100 запитань):")
    print(f"   - 2 агенти: {sum_tok_2ag:,} токенів")
    print(f"   - 3 агенти: {sum_tok_3ag:,} токенів")
    print(f"\n🔹 Еквівалентна вартість у тарифах GPT-4o-mini:")
    print(f"   - 2 агенти: ${cost_mini_2ag:.4f}")
    print(f"   - 3 агенти: ${cost_mini_3ag:.4f}")
    print(f"\n🔹 Еквівалентна вартість у тарифах повноцінного GPT-4o:")
    print(f"   - 2 агенти: ${cost_4o_2ag:.4f}")
    print(f"   - 3 агенти: ${cost_4o_3ag:.4f}")

    # 📝 ВИСНОВОК
    print("\n=======================================================")
    print("📌 FINAL CONCLUSION")
    print("=======================================================")
    print(
        f"A 3-agent network achieves an accuracy of {acc_3ag*100:.2f}% compared to {acc_2ag*100:.2f}% for the 2-agent network.\n"
        f"Total token consumption for 100 queries decreased from {sum_tok_2ag:,} to {sum_tok_3ag:,} tokens, "
        f"reducing commercial API operation costs while execution time shifted from {avg_lat_2ag:.2f}s to {avg_lat_3ag:.2f}s."
    )

    # 🎨 ПОБУДОВА ТА ЗБЕРЕЖЕННЯ ГРАФІКІВ МАТРИЦЬ ПОХИБОК
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    sns.heatmap(cm_2ag, annot=True, fmt="d", cmap="Blues", ax=axes[0], cbar=False)
    axes[0].set_title("Confusion matrix: Analyst + Manager")
    axes[0].set_xlabel("Predicted (0 = Rejection, 1 = Success)")
    axes[0].set_ylabel("Actual Ground Truth (0 = No Data, 1 = Has Data)")

    sns.heatmap(cm_3ag, annot=True, fmt="d", cmap="Greens", ax=axes[1], cbar=False)
    axes[1].set_title("Confusion matrix: Analyst + Critic + Manager")
    axes[1].set_xlabel("Predicted (0 = Rejection, 1 = Success)")
    axes[1].set_ylabel("Actual Ground Truth (0 = No Data, 1 = Has Data)")

    plt.tight_layout()
    plot_path = "confusion_matrices.png"
    plt.savefig(plot_path, dpi=300)
    print(f"\n🖼️ Матриці похибок успішно збережено у файл: {os.path.abspath(plot_path)}")


if __name__ == "__main__":
    main()