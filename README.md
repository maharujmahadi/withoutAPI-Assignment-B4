# Dhaka Building Retrofit Consultant (Streamlit)

This project builds a simple Streamlit web app that:

- Computes a **vulnerability score** (Risk Tier) for a building based on research tables from `Assignment Final.xlsx`.
- Estimates a **retrofit cost** using PWD rates from the same research.
- Includes an **LLM agent integration** using **Mistral (free API)** that calls deterministic Python functions as tools.

## 🔧 Features

### ✅ Deterministic Python tools
- `calculate_vulnerability_score(soil_type, construction_year, soft_story, structure_type)`
- `estimate_retrofit_cost(intervention_type, quantity, zone, num_floors)`  (quantity is in meters or sqm depending on method)

These functions follow the logic extracted from the Excel sheets in `Assignment Final.xlsx`.

### 🤖 Agent integration (Mistral + function calling)
- The agent is forced to extract parameters from a user description.
- It **must** call both tools (score + cost) before returning a final report.
- The final report includes citations to the research-derived scoring and cost tables.

## 🚀 Run Locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set the Mistral API key in your environment:

```bash
setx MISTRAL_API_KEY "<your_api_key>"
```

3. Run the Streamlit app:

```bash
streamlit run streamlit_app.py
```

4. Open the URL shown in your terminal (usually `http://localhost:8501`).

## 🧠 How to Use

- Use **Manual Calculator** mode to directly input parameters and get deterministic results.
- Use **Agent Chat** mode to type natural language building descriptions (e.g., `"5-story building in Mirpur built in 1995 with open ground-floor parking"`) and let the agent parse and compute.

## 🧩 Files

- `tools.py` – deterministic scoring + retrofit cost tools.
- `agent.py` – Mistral integration + tool-calling loop.
- `streamlit_app.py` – Streamlit UI and routing between manual/agent modes.
- `Assignment Final.xlsx` – research source data for scoring and cost.

## 📌 Notes

- The Mistral API is used in a lightweight tool-calling style but may require an API key for execution.
- If you want to adapt this to another LLM provider, update `agent.py`.
