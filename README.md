# MAS AI E-Commerce: Multi-Agent Decision Support System for Dynamic Pricing

An end-to-end neuro-symbolic and multi-agent decision support system for e-commerce dynamic pricing, customer segmentation (RFM + K-Means), and price elasticity ($E_d$) modeling. The repository includes the FastAPI gateway, web interface, n8n multi-agent workflows, SQLite database, 100-query ground-truth benchmark, and automated evaluation suite.

## System Architecture

* **Backend Gateway (`main.py`):** FastAPI service routing user queries to n8n multi-agent pipelines and local Ollama LLMs (`qwen2.5-coder:32b` for SQL generation and `qwen2.5:32b` for analytical synthesis), maintaining session context (`history.json`).
* **Web Interface (`static/`):** Lightweight frontend (`index.html`, `style.css`, `app.js`) for interactive querying, switching between 2-agent and 3-agent modes, and inspecting execution latency/token metrics.
* **n8n Multi-Agent Workflows (`Segmentation.json`, `Interpretation.json`):**
  * **2-Agent Architecture (`Analyst + Manager`):** Translates natural language questions into SQL queries against `ecommerce_data.db` and synthesizes executive pricing recommendations.
  * **3-Agent Architecture (`Analyst + Critic + Manager`):** Adds an automated **Critic** verification layer to audit SQL grounding, detect out-of-distribution/empty-set queries, and validate elasticity-margin trade-offs before final output.

## Repository Contents

* `main.py` & `static/` — FastAPI server and interactive web UI.
* `ecommerce_data.db` & `convert_to_sql.py` — SQLite database (`clients` and `purchases` tables) and ETL conversion script.
* `Segmentation.json` & `Interpretation.json` — Exported n8n workflow definitions.
* `generate_ground_truth.py` & `ground_truth_100.json` / `.xlsx` — Deterministic SQL ground-truth generator and 100-query benchmark (80 scalable block queries including 25 negative/hallucination probes + 20 complex analytical queries).
* `results_2agents_final.json` / `.xlsx` & `results_3agents_final.json` / `.xlsx` — Experimental logs with responses, latency, and token usage.
* `evaluate_pipelines.py`, `calc_tokens.py`, `convert_to_separate_excels.py` — Evaluation scripts for Accuracy, F1-score, hallucination rejection, latency, token consumption, and confusion matrix plotting (`confusion_matrices.png`).

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Web Interface & API Gateway**
   Ensure Ollama (`qwen2.5-coder:32b`, `qwen2.5:32b`) and n8n webhooks are active, then launch FastAPI:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Open `http://localhost:8000` in your browser to interact with the system.

3. **Reproduce Benchmark Evaluation**
   ```bash
   python generate_ground_truth.py
   python evaluate_pipelines.py
   ```