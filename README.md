# Retail Analytics Agent

## Overview

Retail Analytics Agent is a LangGraph-based analytics assistant designed for non-technical retail managers.

The system converts natural language business questions into SQL queries, executes them against BigQuery, and generates executive-level reports.

The agent combines LLM reasoning with analyst-approved historical examples stored in a Golden Knowledge Base to improve SQL generation and report quality.

---

## Features

* Natural language analytics
* BigQuery integration
* Golden Knowledge retrieval (RAG)
* SQL validation and automatic repair
* Executive report generation
* PII masking (emails and phone numbers)
* User-specific report preferences
* Feedback collection
* Observability and execution tracing
* LangGraph orchestration

---

## Technology Stack

| Component       | Technology             |
| --------------- | ---------------------- |
| Agent Framework | LangGraph              |
| LLM             | OpenAI                 |
| Data Warehouse  | Google BigQuery        |
| Vector Store    | ChromaDB               |
| Embeddings      | Sentence Transformers  |
| Configuration   | YAML                   |
| Observability   | JSONL execution traces |

---

## Prerequisites

Before running the project, install:

* Python 3.12+
* uv
* Google Cloud SDK
* OpenAI API key

---

## Installation

Clone the repository:

```bash
git clone https://github.com/affogato15/data_analysis_agent.git
cd data_analysis_agent
```
Install UV

macOS / Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Wondows PowerShell:

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify installation

```bash
uv --version
```
Install dependencies:

```bash
uv sync
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
```

---
## Google Cloud Setup

1. Create a Google Cloud Project.

2. Enable the BigQuery API.

3. Install Google Cloud SDK.

4. Authenticate:

```bash
gcloud auth application-default login
```

5. Set your project:

```bash
gcloud config set project YOUR_PROJECT_ID
```
### Configure Project ID

Update `app/config.yaml`:

```yaml
project_id: YOUR_PROJECT_ID
```
___
## Google Cloud Authentication

Authenticate with Google Cloud:

```bash
gcloud auth application-default login
```

Verify access to BigQuery:

```bash
gcloud auth application-default print-access-token
```

---

## Build the Golden Knowledge Index

Before using the agent, build the vector index:

```bash
uv run python app/golden_indexer.py
```

This will create the Chroma vector store used for Golden Knowledge retrieval.

---

## Run the Application

Start the CLI:

```bash
uv run python -m app.run_app
```

---

## Example Session

```text
User ID: manager_a

Question:
top-10 users with the highest revenue
```

Example report:

```text
# Top 10 Users by Revenue

| user_id | total_orders | total_revenue |
|---------|--------------|---------------|
| 21127   |      3       |    1453.07    |
| ...                                    |

Comments:
- Revenue is concentrated among a small group of customers.
- High-value customers may benefit from retention programs.
```

---

## User Preferences

The agent supports manager-specific preferences.

Example:

```json
{
  "manager_a": {
    "report_format": "table_with_comments",
    "tone": "concise executive"
  },
  "manager_b": {
    "report_format": "bullet_points",
    "tone": "concise executive"
  }
}
```

---

## Project Structure

```text
app/
├── agent_graph.py
├── run_app.py
├── config.yaml

├── sql_engine.py
├── bigquery_executor.py

├── report_generator.py
├── pii_masker.py

├── feedback.py
├── user_preferences.py
├── saved_reports.py

├── observability.py
├── draw_graph.py
├── golden_retriever.py

golden_bucket/
memory/
logs/
vector_store/

README.md
HLD.md
```

---

## Observability

Each execution generates a trace containing:

* Run ID
* Latency
* Retrieved Golden Examples
* Generated SQL
* Repair Attempts
* Execution Errors
* Final Status

Trace logs are stored in:

```text
logs/agent_runs.jsonl
```

---

## Feedback Collection

Users can provide feedback after each response.

Positive feedback is stored as candidate examples for future analyst review and potential inclusion in the Golden Knowledge Base.

---

## Documentation

Detailed architecture, design decisions, requirement coverage, error handling strategy, learning loop design, and deployment considerations can be found in:

```text
HLD.md
```
