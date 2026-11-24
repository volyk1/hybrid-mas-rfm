import sqlite3
import json
import re
import os

DB_PATH = "ecommerce_data.db"
OUTPUT_JSON = "ground_truth_100.json"

# Повний список 100 затверджених питань
QUESTIONS_TEXT = [
    # Block 1
    "[Q1] Show country of origin, purchased items, price elasticity of demand for these items, and cluster membership for customer 13069.",
    "[Q2] Show country of origin, purchased items, price elasticity of demand for these items, and cluster membership for customer 12415.",
    "[Q3] Show country of origin, purchased items, price elasticity of demand for these items, and cluster membership for customer 12347.",
    "[Q4] Show country of origin, purchased items, price elasticity of demand for these items, and cluster membership for customer 12621.",
    "[Q5] Show country of origin, purchased items, price elasticity of demand for these items, and cluster membership for customer 12748.",
    "[Q6] Show country of origin, purchased items, price elasticity of demand for these items, and cluster membership for customer 22222.", #14156
    "[Q7] Show country of origin, purchased items, price elasticity of demand for these items, and cluster membership for customer 33333.", #12356
    "[Q8] Show country of origin, purchased items, price elasticity of demand for these items, and cluster membership for customer 44444.", #12431
    "[Q9] Show country of origin, purchased items, price elasticity of demand for these items, and cluster membership for customer 55555.", #12753
    "[Q10] Show country of origin, purchased items, price elasticity of demand for these items, and cluster membership for customer 66666.", #13089
    # Block 2
    "[Q11] What is the total monetary spend, transaction frequency, and price elasticity of items bought by client 17490?",
    "[Q12] What is the total monetary spend, transaction frequency, and price elasticity of items bought by client 12008?",
    "[Q13] What is the total monetary spend, transaction frequency, and price elasticity of items bought by client 12026?",
    "[Q14] What is the total monetary spend, transaction frequency, and price elasticity of items bought by client 12071?",
    "[Q15] What is the total monetary spend, transaction frequency, and price elasticity of items bought by client 12237?",
    "[Q16] What is the total monetary spend, transaction frequency, and price elasticity of items bought by client 23245?", #12348
    "[Q17] What is the total monetary spend, transaction frequency, and price elasticity of items bought by client 23248?", #12357
    "[Q18] What is the total monetary spend, transaction frequency, and price elasticity of items bought by client 88888?", #12409
    "[Q19] What is the total monetary spend, transaction frequency, and price elasticity of items bought by client 50505?", #12451
    "[Q20] What is the total monetary spend, transaction frequency, and price elasticity of items bought by client 90909?", #12540
    # Block 3
    "[Q21] To which cluster does customer 15804 belong, and what are their primary purchasing activity indicators (recency and average price)?",
    "[Q22] To which cluster does customer 12006 belong, and what are their primary purchasing activity indicators (recency and average price)?",
    "[Q23] To which cluster does customer 12031 belong, and what are their primary purchasing activity indicators (recency and average price)?",
    "[Q24] To which cluster does customer 12042 belong, and what are their primary purchasing activity indicators (recency and average price)?",
    "[Q25] To which cluster does customer 12067 belong, and what are their primary purchasing activity indicators (recency and average price)?",
    "[Q26] To which cluster does customer 44444 belong, and what are their primary purchasing activity indicators (recency and average price)?", #12130
    "[Q27] To which cluster does customer 88888 belong, and what are their primary purchasing activity indicators (recency and average price)?", #12346
    "[Q28] To which cluster does customer 99999 belong, and what are their primary purchasing activity indicators (recency and average price)?", #12370
    "[Q29] To which cluster does customer 77777 belong, and what are their primary purchasing activity indicators (recency and average price)?", #12417
    "[Q30] To which cluster does customer 55555 belong, and what are their primary purchasing activity indicators (recency and average price)?", #12481
    # Block 4
    "[Q31] Identify products with inelastic demand ($E_d < 1$) purchased by customer 12359, and explain what measures can be taken to increase store revenue from customer 12359.",
    "[Q32] Identify products with inelastic demand ($E_d < 1$) purchased by customer 13069, and explain what measures can be taken to increase store revenue from customer 13069.",
    "[Q33] Identify products with inelastic demand ($E_d < 1$) purchased by customer 17490, and explain what measures can be taken to increase store revenue from customer 17490.",
    "[Q34] Identify products with inelastic demand ($E_d < 1$) purchased by customer 15804, and explain what measures can be taken to increase store revenue from customer 15804.",
    "[Q35] Identify products with inelastic demand ($E_d < 1$) purchased by customer 12415, and explain what measures can be taken to increase store revenue from customer 12415.",
    "[Q36] Identify products with inelastic demand ($E_d < 1$) purchased by customer 60606, and explain what measures can be taken to increase store revenue from customer 60606.", #12347
    "[Q37] Identify products with inelastic demand ($E_d < 1$) purchased by customer 45867, and explain what measures can be taken to increase store revenue from customer 45867.", #12621
    "[Q38] Identify products with inelastic demand ($E_d < 1$) purchased by customer 95468, and explain what measures can be taken to increase store revenue from customer 95468.", #12748
    "[Q39] Identify products with inelastic demand ($E_d < 1$) purchased by customer 36482, and explain what measures can be taken to increase store revenue from customer 36482.", #14156
    "[Q40] Identify products with inelastic demand ($E_d < 1$) purchased by customer 90480, and explain what measures can be taken to increase store revenue from customer 90480.", #12356
    # Block 5
    "[Q41] Based on transaction history, what dynamic pricing strategy should be applied to client 16949 to maximize customer lifetime value?",
    "[Q42] Based on transaction history, what dynamic pricing strategy should be applied to client 13069 to maximize customer lifetime value?",
    "[Q43] Based on transaction history, what dynamic pricing strategy should be applied to client 17490 to maximize customer lifetime value?",
    "[Q44] Based on transaction history, what dynamic pricing strategy should be applied to client 15804 to maximize customer lifetime value?",
    "[Q45] Based on transaction history, what dynamic pricing strategy should be applied to client 12359 to maximize customer lifetime value?",
    "[Q46] Based on transaction history, what dynamic pricing strategy should be applied to client 72691 to maximize customer lifetime value?", #12415
    "[Q47] Based on transaction history, what dynamic pricing strategy should be applied to client 97239 to maximize customer lifetime value?", #12347
    "[Q48] Based on transaction history, what dynamic pricing strategy should be applied to client 65380 to maximize customer lifetime value?", #12621
    "[Q49] Based on transaction history, what dynamic pricing strategy should be applied to client 99364 to maximize customer lifetime value?", #12748
    "[Q50] Based on transaction history, what dynamic pricing strategy should be applied to client 84390 to maximize customer lifetime value?", #14156
    # Block 6
    "[Q51] Find top 5 products with elastic demand ($E_d > 1$) purchased by clients in Cluster 0 and suggest optimal pricing.",
    "[Q52] Find top 5 products with elastic demand ($E_d > 1$) purchased by clients in Cluster 1 and suggest optimal pricing.",
    "[Q53] Find top 5 products with elastic demand ($E_d > 1$) purchased by clients in Cluster 4 and suggest optimal pricing.", #2
    "[Q54] Find top 5 products with elastic demand ($E_d > 1$) purchased by clients in Cluster 6 and suggest optimal pricing.", #3
    "[Q55] Find top 5 products with elastic demand ($E_d > 1$) purchased by client 13408 and suggest strategic price adjustments.",
    "[Q56] Find top 5 products with elastic demand ($E_d > 1$) purchased by client 13798 and suggest strategic price adjustments.",
    "[Q57] Find top 5 products with elastic demand ($E_d > 1$) purchased by client 12008 and suggest strategic price adjustments.",
    "[Q58] Find top 5 products with elastic demand ($E_d > 1$) purchased by client 55698 and suggest strategic price adjustments.", #12026
    "[Q59] Find top 5 products with elastic demand ($E_d > 1$) purchased by client 60730 and suggest strategic price adjustments.", #12071
    "[Q60] Find top 5 products with elastic demand ($E_d > 1$) purchased by client 99999 and suggest strategic price adjustments.", #12237
    # Block 7
    "[Q61] Which products purchased by clients from Germany exhibit elastic demand, and what are their average prices?",
    "[Q62] Which products purchased by clients from France exhibit elastic demand, and what are their average prices?",
    "[Q63] Which products purchased by clients from Australia exhibit elastic demand, and what are their average prices?",
    "[Q64] Which products purchased by clients from Norway exhibit elastic demand, and what are their average prices?",
    "[Q65] Which products purchased by clients from Belgium exhibit elastic demand, and what are their average prices?",
    "[Q66] Which products purchased by clients from Moroco exhibit elastic demand, and what are their average prices?", #Ireland
    "[Q67] Which products purchased by clients from China exhibit elastic demand, and what are their average prices?", #Switzerland
    "[Q68] Which products purchased by clients from Iran exhibit elastic demand, and what are their average prices?", #Cyprus
    "[Q69] Which products purchased by clients from Uganda exhibit elastic demand, and what are their average prices?", #Denmark
    "[Q70] Which products purchased by clients from Ukraine exhibit elastic demand, and what are their average prices?", #Spain
    # Block 8
    "[Q71] List all items with near-unitary elasticity ($E_d \\approx 1$) bought by clients in Cluster 0 and specify purchase frequencies.",
    "[Q72] List all items with near-unitary elasticity ($E_d \\approx 1$) bought by clients in Cluster 1 and specify purchase frequencies.",
    "[Q73] List all items with near-unitary elasticity ($E_d \\approx 1$) bought by clients in Cluster 4 and specify purchase frequencies.", #2
    "[Q74] List all items with near-unitary elasticity ($E_d \\approx 1$) bought by clients in Cluster 6 and specify purchase frequencies.", #3
    "[Q75] List all items with near-unitary elasticity ($0.95 \\le E_d \\le 1.05$) bought by clients from the United Kingdom.",
    "[Q76] Identify items purchased by customer 13069 that exhibit near-unitary elasticity ($E_d \\approx 1$) and analyze profit impact.",
    "[Q77] Identify items purchased by customer 17490 that exhibit near-unitary elasticity ($E_d \\approx 1$) and analyze profit impact.",
    "[Q78] Identify items purchased by customer 90909 that exhibit near-unitary elasticity ($E_d \\approx 1$) and analyze profit impact.", #12415
    "[Q79] Identify items purchased by customer 80808 that exhibit near-unitary elasticity ($E_d \\approx 1$) and analyze profit impact.", #12347
    "[Q80] Identify items purchased by customer 75694 that exhibit near-unitary elasticity ($E_d \\approx 1$) and analyze profit impact.", #12621
    # Part 2: Unique Questions
    "[Q81] Find the top 5 products with the highest overall price elasticity of demand ($E_d > 1$) in the database and provide optimal pricing recommendations.",
    "[Q82] List all items with near-unitary elasticity rounded to one decimal place ($1.01 <= E_d <= 1.04$) and specify which cluster's clients bought them most frequently.",
    "[Q83] Compare the average transaction monetary value between representative clients from Cluster 0 and Cluster 2.",
    "[Q84] Compare the average transaction monetary value between representative clients from Cluster 1 and Cluster 3.",
    "[Q85] Evaluate the overall elasticity distribution across all identified clusters and summarize key risks for price increase strategies.",
    "[Q86] Compare total monetary expenditure, purchase frequency, and elasticity profiles between Cluster 0 and Cluster 1.",
    "[Q87] Compare monetary spend and product elasticity ranges between representative clients in Cluster 0 and Cluster 2.",
    "[Q88] Compare average price per item and recency indicators between clients belonging to Cluster 1 and Cluster 3.",
    "[Q89] Compare Christmas product purchasing propensity (BoughtChristmas) between Cluster 0 and Cluster 3.",
    "[Q90] Compare set product purchasing propensity (BoughtSet) between clients in Cluster 2 and Cluster 3.",
    "[Q91] Identify top 5 products with price elasticity $E_d > 1.2$ in the database and assess the sensitivity of demand to price changes.",
    "[Q92] List inelastic products ($E_d < 1$) in Cluster 2 and propose margin improvement measures without impacting purchased quantities (Quantity).",
    "[Q93] Provide a comparative evaluation of high-value vs. churn-risk clusters based on all three RFM metrics (Recency, Frequency, Monetary spend).",
    "[Q94] Evaluate the elasticity distribution across Cluster 0 (specifying product counts for elastic, inelastic, and unitary types) and summarize key operational risks for margin expansion.",
    "[Q95] Evaluate the elasticity distribution across Cluster 2 (specifying product counts for elastic, inelastic, and unitary types) and summarize key operational risks for price increase strategies.",
    "[Q96] Evaluate the elasticity distribution across Cluster 3 (specifying product counts for elastic, inelastic, and unitary types) and summarize customer churn risks associated with price modifications.",
    "[Q97] Synthesize multi-agent recommendations regarding dynamic discounting and cross-selling strategies for high-frequency purchasing segments, differentiating between low-cost and high-cost products.",
    "[Q98] Which product categories in the database generate the highest total revenue despite having elastic demand ($E_d > 1$)?",
    "[Q99] Analyze the proportion of expenditure spent on set products (BoughtSet = 1) relative to total customer monetary spend across different segments.",
    "[Q100] Summarize key decision-making criteria for Critic and Manager agents when resolving elasticity-margin trade-offs specifically within Cluster 2 (High-Value Loyal Clients)."
]

def parse_questions():
    parsed = []
    for line in QUESTIONS_TEXT:
        match = re.match(r'^\[Q(\d+)\]\s+(.*)', line)
        if match:
            parsed.append({"id": int(match.group(1)), "text": match.group(2)})
    return parsed

def solve_all_questions():
    if not os.path.exists(DB_PATH):
        print(f"❌ Базу даних {DB_PATH} не знайдено! Переконайтеся, що файл знаходиться в папці проєкту.")
        return

    questions = parse_questions()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    results = []
    
    for q in questions:
        q_id = q["id"]
        q_text = q["text"]
        
        sql_query = ""
        category = ""
        
        # --- BLOCK 1 ---
        if 1 <= q_id <= 10:
            category = "Block 1: Customer Profile"
            cust_id = re.search(r'customer\s+(\d+)', q_text, re.IGNORECASE).group(1)
            sql_query = f"SELECT c.CustomerNo, c.Cluster, p.Country, p.ProductName, p.Price, p.Quantity, p.Elasticity FROM clients c LEFT JOIN purchases p ON c.CustomerNo = p.CustomerNo WHERE c.CustomerNo = {cust_id} LIMIT 10;"

        # --- BLOCK 2 ---
        elif 11 <= q_id <= 20:
            category = "Block 2: RFM & Elasticity"
            cust_id = re.search(r'client\s+(\d+)', q_text, re.IGNORECASE).group(1)
            sql_query = f"SELECT c.CustomerNo, c.Monetary, c.Frequency, AVG(p.Elasticity) as AvgPriceElasticity FROM clients c LEFT JOIN purchases p ON c.CustomerNo = p.CustomerNo WHERE c.CustomerNo = {cust_id} GROUP BY c.CustomerNo;"

        # --- BLOCK 3 ---
        elif 21 <= q_id <= 30:
            category = "Block 3: Cluster & Activity"
            cust_id = re.search(r'customer\s+(\d+)', q_text, re.IGNORECASE).group(1)
            sql_query = f"SELECT CustomerNo, Cluster, Recency, AvgPrice FROM clients WHERE CustomerNo = {cust_id};"

        # --- BLOCK 4 ---
        elif 31 <= q_id <= 40:
            category = "Block 4: Inelastic Demand"
            cust_id = re.search(r'customer\s+(\d+)', q_text, re.IGNORECASE).group(1)
            sql_query = f"SELECT ProductName, Price, Quantity, Elasticity FROM purchases WHERE CustomerNo = {cust_id} AND Elasticity < 1 AND Elasticity > 0 GROUP BY ProductName ORDER BY Elasticity ASC LIMIT 10;"

        # --- BLOCK 5 ---
        elif 41 <= q_id <= 50:
            category = "Block 5: Dynamic Pricing Plan"
            cust_id = re.search(r'client\s+(\d+)', q_text, re.IGNORECASE).group(1)
            sql_query = f"SELECT c.CustomerNo, c.Cluster, c.Recency, c.Frequency, c.Monetary, AVG(p.Elasticity) as AvgElasticity FROM clients c LEFT JOIN purchases p ON c.CustomerNo = p.CustomerNo WHERE c.CustomerNo = {cust_id} GROUP BY c.CustomerNo;"

        # --- BLOCK 6 ---
        elif 51 <= q_id <= 60:
            category = "Block 6: Elastic Goods Analysis"
            cluster_match = re.search(r'Cluster\s+(\d+)', q_text)
            client_match = re.search(r'client\s+(\d+)', q_text)
            
            if cluster_match:
                cluster_id = cluster_match.group(1)
                sql_query = f"SELECT p.ProductName, AVG(p.Price) as AvgPrice, SUM(p.Quantity) as TotalQuantity, AVG(p.Elasticity) as Elasticity FROM purchases p JOIN clients c ON p.CustomerNo = c.CustomerNo WHERE c.Cluster = {cluster_id} AND p.Elasticity > 1 GROUP BY p.ProductName ORDER BY Elasticity DESC LIMIT 5;"
            elif client_match:
                cust_id = client_match.group(1)
                sql_query = f"SELECT ProductName, AVG(Price) as AvgPrice, SUM(Quantity) as TotalQuantity, AVG(Elasticity) as Elasticity FROM purchases WHERE CustomerNo = {cust_id} AND Elasticity > 1 GROUP BY ProductName ORDER BY Elasticity DESC LIMIT 5;"

        # --- BLOCK 7 ---
        elif 61 <= q_id <= 70:
            category = "Block 7: Country Elasticity"
            country_match = re.search(r'from\s+([A-Za-z\s\(\)]+)\s+exhibit', q_text)
            country = country_match.group(1).strip() if country_match else "Germany"
            if "Ireland" in country: 
                country = "EIRE"
            sql_query = f"SELECT ProductName, AVG(Price) as AvgPrice, AVG(Elasticity) as AvgElasticity FROM purchases WHERE Country LIKE '%{country}%' AND Elasticity > 1 GROUP BY ProductName ORDER BY AvgElasticity DESC LIMIT 10;"

        # --- BLOCK 8 ---
        elif 71 <= q_id <= 80:
            category = "Block 8: Near-Unitary Elasticity"
            cluster_match = re.search(r'Cluster\s+(\d+)', q_text)
            client_match = re.search(r'customer\s+(\d+)', q_text)
            country_match = re.search(r'United Kingdom', q_text)

            if cluster_match:
                cluster_id = cluster_match.group(1)
                sql_query = f"SELECT p.ProductName, COUNT(p.TransactionNo) as PurchaseFrequency, AVG(p.Elasticity) as Elasticity FROM purchases p JOIN clients c ON p.CustomerNo = c.CustomerNo WHERE c.Cluster = {cluster_id} AND ABS(p.Elasticity - 1.0) <= 0.1 GROUP BY p.ProductName ORDER BY PurchaseFrequency DESC LIMIT 10;"
            elif country_match:
                sql_query = f"SELECT ProductName, COUNT(TransactionNo) as PurchaseFrequency, AVG(Elasticity) as Elasticity FROM purchases WHERE Country = 'United Kingdom' AND Elasticity BETWEEN 0.95 AND 1.05 GROUP BY ProductName ORDER BY PurchaseFrequency DESC LIMIT 10;"
            elif client_match:
                cust_id = client_match.group(1)
                sql_query = f"SELECT ProductName, Price, Quantity, Elasticity FROM purchases WHERE CustomerNo = {cust_id} AND ABS(Elasticity - 1.0) <= 0.1 GROUP BY ProductName LIMIT 10;"

        # --- PART 2: UNIQUE QUESTIONS ---
        else:
            category = "Part 2: Unique Questions"
            
            if q_id == 81:
                sql_query = "SELECT ProductName, AVG(Price) as Price, SUM(Quantity) as Quantity, AVG(Elasticity) as Elasticity FROM purchases WHERE Elasticity > 1 GROUP BY ProductName ORDER BY Elasticity DESC LIMIT 5;"
            elif q_id == 82:
                sql_query = "SELECT p.ProductName, c.Cluster, COUNT(*) as PurchaseFrequency, ROUND(AVG(p.Elasticity), 1) as RoundedElasticity FROM purchases p JOIN clients c ON p.CustomerNo = c.CustomerNo WHERE p.Elasticity BETWEEN 1.01 AND 1.04 GROUP BY p.ProductName, c.Cluster ORDER BY PurchaseFrequency DESC LIMIT 10;"
            elif q_id == 83:
                sql_query = "SELECT Cluster, AVG(Monetary/Frequency) as AvgTransactionMonetaryValue FROM clients WHERE Cluster IN (0, 2) GROUP BY Cluster;"
            elif q_id == 84:
                sql_query = "SELECT Cluster, AVG(Monetary/Frequency) as AvgTransactionMonetaryValue FROM clients WHERE Cluster IN (1, 3) GROUP BY Cluster;"
            elif q_id == 85:
                sql_query = "SELECT c.Cluster, CASE WHEN p.Elasticity > 1 THEN 'Elastic' WHEN p.Elasticity < 1 THEN 'Inelastic' ELSE 'Unitary' END as DemandType, COUNT(*) as ItemCount FROM purchases p JOIN clients c ON p.CustomerNo = c.CustomerNo GROUP BY c.Cluster, DemandType;"
            elif q_id == 86:
                sql_query = "SELECT c.Cluster, SUM(c.Monetary) as TotalMonetary, AVG(c.Frequency) as AvgFrequency, AVG(p.Elasticity) as AvgElasticity FROM clients c JOIN purchases p ON c.CustomerNo = p.CustomerNo WHERE c.Cluster IN (0, 1) GROUP BY c.Cluster;"
            elif q_id == 87:
                sql_query = "SELECT c.Cluster, AVG(c.Monetary) as AvgSpend, MIN(p.Elasticity) as MinElasticity, MAX(p.Elasticity) as MaxElasticity FROM clients c JOIN purchases p ON c.CustomerNo = p.CustomerNo WHERE c.Cluster IN (0, 2) GROUP BY c.Cluster;"
            elif q_id == 88:
                sql_query = "SELECT Cluster, AVG(AvgPrice) as MeanPrice, AVG(Recency) as MeanRecency FROM clients WHERE Cluster IN (1, 3) GROUP BY Cluster;"
            elif q_id == 89:
                sql_query = "SELECT Cluster, AVG(BoughtChristmas) * 100 as ChristmasPurchasePercentage FROM clients WHERE Cluster IN (0, 3) GROUP BY Cluster;"
            elif q_id == 90:
                sql_query = "SELECT Cluster, AVG(BoughtSet) * 100 as SetPurchasePercentage FROM clients WHERE Cluster IN (2, 3) GROUP BY Cluster;"
            elif q_id == 91:
                sql_query = "SELECT ProductName, AVG(Price) as Price, SUM(Quantity) as Quantity, AVG(Elasticity) as Elasticity FROM purchases WHERE Elasticity > 1.2 GROUP BY ProductName ORDER BY Elasticity DESC LIMIT 5;"
            elif q_id == 92:
                sql_query = "SELECT p.ProductName, AVG(p.Price) as Price, SUM(p.Quantity) as TotalQuantity, AVG(p.Elasticity) as Elasticity FROM purchases p JOIN clients c ON p.CustomerNo = c.CustomerNo WHERE c.Cluster = 2 AND p.Elasticity < 1 GROUP BY p.ProductName ORDER BY TotalQuantity DESC LIMIT 10;"
            elif q_id == 93:
                sql_query = "SELECT Cluster, AVG(Recency) as AvgRecency, AVG(Frequency) as AvgFrequency, AVG(Monetary) as AvgMonetary FROM clients GROUP BY Cluster;"
            elif q_id == 94:
                sql_query = "SELECT CASE WHEN p.Elasticity > 1 THEN 'Elastic' WHEN p.Elasticity < 1 THEN 'Inelastic' ELSE 'Unitary' END as Category, COUNT(DISTINCT p.ProductName) as ProductCount FROM purchases p JOIN clients c ON p.CustomerNo = c.CustomerNo WHERE c.Cluster = 0 GROUP BY Category;"
            elif q_id == 95:
                sql_query = "SELECT CASE WHEN p.Elasticity > 1 THEN 'Elastic' WHEN p.Elasticity < 1 THEN 'Inelastic' ELSE 'Unitary' END as Category, COUNT(DISTINCT p.ProductName) as ProductCount FROM purchases p JOIN clients c ON p.CustomerNo = c.CustomerNo WHERE c.Cluster = 2 GROUP BY Category;"
            elif q_id == 96:
                sql_query = "SELECT CASE WHEN p.Elasticity > 1 THEN 'Elastic' WHEN p.Elasticity < 1 THEN 'Inelastic' ELSE 'Unitary' END as Category, COUNT(DISTINCT p.ProductName) as ProductCount FROM purchases p JOIN clients c ON p.CustomerNo = c.CustomerNo WHERE c.Cluster = 3 GROUP BY Category;"
            elif q_id == 97:
                sql_query = "SELECT CASE WHEN Price >= 15 THEN 'High-Cost' ELSE 'Low-Cost' END as PriceCategory, AVG(Elasticity) as AvgElasticity, SUM(Quantity) as TotalQty FROM purchases GROUP BY PriceCategory;"
            elif q_id == 98:
                sql_query = "SELECT ProductName, SUM(Price * Quantity) as TotalRevenue, AVG(Elasticity) as Elasticity FROM purchases WHERE Elasticity > 1 GROUP BY ProductName ORDER BY TotalRevenue DESC LIMIT 5;"
            elif q_id == 99:
                sql_query = "SELECT BoughtSet, SUM(Monetary) as GroupMonetary, AVG(Monetary) as AvgSpend FROM clients GROUP BY BoughtSet;"
            elif q_id == 100:
                sql_query = "SELECT c.Cluster, COUNT(DISTINCT c.CustomerNo) as TotalClients, AVG(c.Monetary) as AvgSpend, AVG(p.Elasticity) as AvgElasticity FROM clients c JOIN purchases p ON c.CustomerNo = p.CustomerNo WHERE c.Cluster = 2 GROUP BY c.Cluster;"

        # Виконуємо запит та записуємо результат
        cursor.execute(sql_query)
        db_rows = [dict(r) for r in cursor.fetchall()]

        results.append({
            "question_id": q_id,
            "category": category,
            "question_text": q_text,
            "sql_query": sql_query,
            "ground_truth_output": db_rows
        })

    conn.close()

    # Зберігаємо результат у ground_truth_100.json
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"🎉 ВСЕ ІДЕАЛЬНО! Усі 100 питань та точні відповіді записано у -> {OUTPUT_JSON}")

if __name__ == "__main__":
    solve_all_questions()