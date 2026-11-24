import json
import os
import pandas as pd

# 📁 Список файлів для конвертації (вхідний JSON -> вихідний XLSX)
FILES_TO_CONVERT = [
    ("ground_truth_100.json", "ground_truth_100.xlsx"),
    ("results_2agents.json", "results_2agents.xlsx"),
    ("results_3agents.json", "results_3agents.xlsx"),
]


def convert_json_to_excel(json_path, excel_path):
  if not os.path.exists(json_path):
    print(f"⚠️ Файл {json_path} не знайдено!")
    return

  with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

  # Якщо ground_truth є вкладеним списком/об'єктом, перетворюємо його на JSON-стрічку
  for item in data:
    if "ground_truth" in item and isinstance(item["ground_truth"], (list, dict)):
      item["ground_truth"] = json.dumps(
          item["ground_truth"], ensure_ascii=False
      )

  df = pd.DataFrame(data)
  df.to_excel(excel_path, index=False, engine="openpyxl")
  print(f"✅ Успішно створено: {excel_path} ({len(df)} рядків)")


def main():
  print("🚀 Створення окремих Excel-файлів...\n")
  for json_file, excel_file in FILES_TO_CONVERT:
    convert_json_to_excel(json_file, excel_file)
  print("\n🎉 Готово! Усі 3 файли знаходяться у вашій папці.")


if __name__ == "__main__":
  main()