from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml
from openai import OpenAI
from pydantic import BaseModel, Field


class ReportOutput(BaseModel):
    report_markdown: str = Field(
        description="Final executive report in markdown."
    )


def dataframe_to_context(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "The query returned no rows."

    preview = df.head(max_rows).to_markdown(index=False)

    return f"""
Rows returned: {len(df)}
Columns: {", ".join(df.columns)}

Data preview:
{preview}
"""


def get_format_instruction(report_format: str) -> str:
    if report_format == "table_with_comments":
        return """
Return the report in this exact markdown structure:

# <Short title>

## Data Table
Include a markdown table based on the query result.

## Comments
- 3 to 5 concise business comments explaining what the table means.

## Limitations
- Mention relevant assumptions or data limitations.
"""

    if report_format == "tabular_data_with_comments":
        return """
Return the report in this exact markdown structure:

# <Short title>

## Data Table
Include a markdown table based on the query result.

## Comments
- 3 to 5 concise business comments explaining what the table means.

## Limitations
- Mention relevant assumptions or data limitations.
"""

    return """
Return the report in this exact markdown structure:

# <Short title>

## Summary
A short executive summary.

## Key Findings
- 3 to 5 concise bullet points.

## Recommendations
- 2 to 4 practical business recommendations.

## Limitations
- Mention relevant assumptions or data limitations.
"""


class ReportGenerator:
    def __init__(self, config_path: Path):
        self.config = yaml.safe_load(
            config_path.read_text(encoding="utf-8")
        )

        self.llm_model = self.config["llm"]["model"]
        self.client = OpenAI()

        self.persona = self.config.get("report_persona", {})
        self.tone = self.persona.get("tone", "concise executive")
        self.format_style = self.persona.get("format", "bullet_points")

    def generate_report(
        self,
        question: str,
        sql: str,
        df: pd.DataFrame,
        golden_examples: list[dict],
        user_preferences: dict | None = None,
    ) -> str:
        user_preferences = user_preferences or {}

        report_format = user_preferences.get("report_format", self.format_style)
        tone = user_preferences.get("tone", self.tone)
        format_instruction = get_format_instruction(report_format)

        data_context = dataframe_to_context(df)

        example_reports = "\n\n".join(
            f"""
Example Question:
{ex["question"]}

Example Analyst Report:
{ex["report"]}
"""
            for ex in golden_examples
        )

        prompt = f"""
You are a senior retail data analyst writing for non-technical store and regional managers.

USER QUESTION:
{question}

SQL USED:
{sql}

QUERY RESULT:
{data_context}

RELEVANT ANALYST-APPROVED REPORT EXAMPLES:
{example_reports}

REPORT STYLE:
- Tone: {tone}
- Format preference: {report_format}

FORMAT INSTRUCTIONS:
{format_instruction}

RULES:
- Write for non-technical executives.
- Explain what the numbers mean, not how SQL works.
- Do not mention internal table names unless necessary.
- Do not expose PII.
- Do not invent numbers not present in the query result.
- If the result is empty, explain that no matching data was found and suggest what to check.
- Keep the report concise.
"""

        response = self.client.responses.parse(
            model=self.llm_model,
            input=[
                {
                    "role": "system",
                    "content": "You generate concise executive analytics reports in markdown.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            text_format=ReportOutput,
        )

        return response.output_parsed.report_markdown