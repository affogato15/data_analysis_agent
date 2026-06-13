from __future__ import annotations

import re
from pathlib import Path

import yaml
from openai import OpenAI
from google.cloud import bigquery
from pydantic import BaseModel, Field


DATASET = "bigquery-public-data.thelook_ecommerce"


class SQLGenerationOutput(BaseModel):
    sql: str = Field(description="Valid BigQuery SELECT query only.")


def clean_sql(raw_sql: str) -> str:
    return (
        raw_sql.strip()
        .replace("```sql", "")
        .replace("```", "")
        .strip()
    )


def format_golden_examples(examples: list[dict]) -> str:
    return "\n\n".join(
        f"""
Example {i + 1}

Question:
{ex["question"]}

Business Logic:
{ex["business_logic"]}

SQL:
{ex["sql"]}
"""
        for i, ex in enumerate(examples)
    )


class SQLEngine:
    def __init__(self, config_path: Path):
        self.config = yaml.safe_load(
            config_path.read_text(encoding="utf-8")
        )

        self.project_id = self.config["project_id"]
        self.max_bytes_billed = self.config["max_bytes_billed"]

        self.llm_client = OpenAI()
        self.llm_model = self.config["llm"]["model"]

        self.allowed_tables = [
            table
            for table in self.config["security"]["allowed_tables"]
            if table
        ]

        self.relationships = self.config["schema"].get("relationships", [])
        self.business_rules = self.config["schema"].get("business_rules", [])

        self.bq_client = bigquery.Client(project=self.project_id)

    def get_table_schema(self, table_name: str) -> list[dict]:
        table_id = f"{DATASET}.{table_name}"
        table = self.bq_client.get_table(table_id)

        return [
            {
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,
            }
            for field in table.schema
        ]

    def build_schema_context(self) -> str:
        table_blocks = []

        for table_name in self.allowed_tables:
            schema = self.get_table_schema(table_name)

            columns = "\n".join(
                f"- {col['name']} ({col['type']}, {col['mode']})"
                for col in schema
            )

            table_blocks.append(
                f"""
Table: {table_name}
Full name: `{DATASET}.{table_name}`

Columns:
{columns}
"""
            )

        relationships_text = "\n".join(
            f"- {rel}" for rel in self.relationships
        )

        business_rules_text = "\n".join(
            f"- {rule}" for rule in self.business_rules
        )

        return f"""
DATABASE SCHEMA

{chr(10).join(table_blocks)}

TABLE RELATIONSHIPS

{relationships_text}

BUSINESS RULES

{business_rules_text}
"""

    def generate_sql(
        self,
        question: str,
        golden_examples: list[dict],
    ) -> str:
        schema_context = self.build_schema_context()
        examples_text = format_golden_examples(golden_examples)

        prompt = f"""
You are a senior retail data analyst.

Generate a valid BigQuery SQL query for the user's question.

{schema_context}

ANALYST-APPROVED GOLDEN EXAMPLES

{examples_text}

USER QUESTION

{question}

RULES

- Return only a BigQuery SQL query.
- Use only the provided tables and columns.
- Use fully qualified BigQuery table names.
- Use only SELECT or WITH statements.
- Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE.
- Do not select or expose email, phone or other PII fields.
- Prefer completed orders when calculating revenue, spend, or customer value.
- Add LIMIT 100 for non-aggregated result sets.
"""

        response = self.llm_client.responses.parse(
            model=self.llm_model,
            input=[
                {
                    "role": "system",
                    "content": "You generate safe BigQuery SQL only.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            text_format=SQLGenerationOutput,
        )

        return clean_sql(response.output_parsed.sql)

    def validate_sql(self, sql: str) -> None:
        lowered = sql.lower().strip()

        if not lowered.startswith("select") and not lowered.startswith("with"):
            raise ValueError("Only SELECT/WITH queries are allowed.")

        forbidden = [
            "insert",
            "update",
            "delete",
            "drop",
            "alter",
            "create",
            "truncate",
            "merge",
        ]

        for word in forbidden:
            if re.search(rf"\b{word}\b", lowered):
                raise ValueError(f"Forbidden SQL operation detected: {word}")

        pii_terms = [
            "email",
            "phone",
            #"street_address",
            #"postal_code",
        ]

        for term in pii_terms:
            if re.search(rf"\b{term}\b", lowered):
                raise ValueError(f"PII field detected in SQL: {term}")

        allowed_full_tables = {
            f"`{DATASET}.{table}`".lower()
            for table in self.allowed_tables
        }

        referenced_tables = re.findall(r"`[^`]+`", lowered)

        for table_ref in referenced_tables:
            if table_ref not in allowed_full_tables:
                raise ValueError(f"Table is not allowed: {table_ref}")

    def repair_sql(
            self,
            question: str,
            failed_sql: str,
            error_message: str,
            golden_examples: list[dict],
    ) -> str:
        schema_context = self.build_schema_context()
        examples_text = format_golden_examples(golden_examples)

        prompt = f"""
    You are an expert BigQuery SQL engineer.

    The previous SQL query failed. Generate a corrected BigQuery SQL query.

    DATABASE SCHEMA

    {schema_context}

    ANALYST-APPROVED GOLDEN EXAMPLES

    {examples_text}

    USER QUESTION

    {question}

    FAILED SQL

    {failed_sql}

    ERROR MESSAGE

    {error_message}

    RULES

    - Return only a valid BigQuery SQL query.
    - Preserve the original user intent.
    - Fix only the cause of the SQL failure.
    - Use only the provided tables and columns.
    - Use fully qualified BigQuery table names.
    - Use only SELECT or WITH statements.
    - Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE.
    - Do not select or expose email, phone or other PII fields.
    - Prefer completed orders when calculating revenue, spend, or customer value.
    - Add LIMIT 100 for non-aggregated result sets.
    """

        response = self.llm_client.responses.parse(
            model=self.llm_model,
            input=[
                {
                    "role": "system",
                    "content": "You repair failed BigQuery SQL safely.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            text_format=SQLGenerationOutput,
        )

        return clean_sql(response.output_parsed.sql)

