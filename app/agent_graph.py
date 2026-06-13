from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import pandas as pd
import yaml
from langgraph.graph import END, StateGraph

from app.bigquery_executor import BigQueryExecutor
from app.report_generator import ReportGenerator
from app.sql_engine import SQLEngine
from app.golden_indexer import GoldenRetriever
from app.trace import AgentTrace
from app.pii_masker import mask_dataframe_pii, mask_text_pii

class AgentState(TypedDict, total=False):
    question: str
    golden_examples: list[dict]
    sql: str
    df: pd.DataFrame
    report: str
    attempt: int
    max_sql_retries: int
    error_message: str | None
    status: str
    trace: AgentTrace
    user_id: str
    user_preferences: dict


def build_agent_graph(base_dir: Path):
    config_path = base_dir / "app" / "config.yaml"

    config = yaml.safe_load(
        config_path.read_text(encoding="utf-8")
    )

    retriever = GoldenRetriever(
        golden_trios_path=base_dir / config["paths"]["golden_bucket"],
        vector_store_path=base_dir / config["paths"]["vector_store"],
    )

    sql_engine = SQLEngine(
        config_path=config_path,
    )

    executor = BigQueryExecutor(
        project_id=config["project_id"],
        max_bytes_billed=config["max_bytes_billed"],
    )

    report_generator = ReportGenerator(
        config_path=config_path,
    )

    max_sql_retries = config["agent"]["max_sql_retries"]
    top_k = config["retrieval"]["top_k"]

    def retrieve_examples_node(state: AgentState) -> AgentState:
        examples = retriever.retrieve(
            question=state["question"],
            top_k=top_k,
        )
        trace = AgentTrace(base_dir / "logs" / "agent_runs.jsonl")

        trace.node(
            "retrieve_examples",
            question=state["question"],
            retrieved_examples=[ex["id"] for ex in examples],
        )

        return {
            **state,
            "golden_examples": examples,
            "attempt": 0,
            "max_sql_retries": max_sql_retries,
            "error_message": None,
            "status": "examples_retrieved",
            "trace": trace,
        }

    def generate_sql_node(state: AgentState) -> AgentState:
        sql = sql_engine.generate_sql(
            question=state["question"],
            golden_examples=state["golden_examples"],
        )
        state["trace"].node(
            "generate_sql",
            generated_sql=sql,
        )

        return {
            **state,
            "sql": sql,
            "status": "sql_generated",
        }

    def execute_sql_node(state: AgentState) -> AgentState:
        try:
            sql_engine.validate_sql(state["sql"])

            df = executor.execute_query(state["sql"])
            df = mask_dataframe_pii(df)

            state["trace"].node(
                "execute_sql",
                sql=state["sql"],
                rows_returned=len(df),
            )

            return {
                **state,
                "df": df,
                "error_message": None,
                "status": "sql_executed",
            }

        except Exception as e:

            state["trace"].node(
                "execute_sql_failed",
                error=str(e)
            )

            return {
                **state,
                "error_message": str(e),
                "status": "sql_failed",
            }

    def repair_sql_node(state: AgentState) -> AgentState:
        repaired_sql = sql_engine.repair_sql(
            question=state["question"],
            failed_sql=state["sql"],
            error_message=state["error_message"] or "",
            golden_examples=state["golden_examples"],
        )

        state["trace"].node(
            "repair_sql",
            attempt=state.get("attempt", 0) + 1,
            error=state["error_message"],
            repaired_sql=repaired_sql,
        )

        return {
            **state,
            "sql": repaired_sql,
            "attempt": state.get("attempt", 0) + 1,
            "status": "sql_repaired",
        }

    def generate_report_node(state: AgentState) -> AgentState:
        report = report_generator.generate_report(
            question=state["question"],
            sql=state["sql"],
            df=state["df"],
            golden_examples=state["golden_examples"],
            user_preferences=state.get("user_preferences", {}),
        )
        report = mask_text_pii(report)

        state["trace"].node(
            "generate_report",
            rows_returned=len(state["df"])
        )

        state["trace"].finish(
            status="success",
            question=state["question"],
            user_id=state.get("user_id"),
            user_preferences=state.get("user_preferences", {}),
            repair_attempts=state.get("attempt", 0),
            rows_returned=len(state["df"]),
            retrieved_examples=[ex["id"] for ex in state["golden_examples"]],
            final_sql=state["sql"],
        )

        return {
            **state,
            "report": report,
            "status": "report_generated",
        }

    def route_after_execute(state: AgentState) -> str:
        if state["status"] == "sql_executed":
            return "generate_report"

        if state.get("attempt", 0) < state["max_sql_retries"]:
            return "repair_sql"

        return "fail"

    def fail_node(state: AgentState) -> AgentState:
        state["trace"].finish(
                                status="failed",
                                question=state["question"],
                                user_id=state.get("user_id"),
                                user_preferences=state.get("user_preferences", {}),
                                error_message=state["error_message"],
                                repair_attempts=state["attempt"],
                            )
        return {
            **state,
            "report": (
                "I could not generate a valid SQL query after "
                f"{state['max_sql_retries']} repair attempt(s). "
                f"Last error: {state.get('error_message')}"
            ),
            "status": "failed",
        }

    graph = StateGraph(AgentState)

    graph.add_node("retrieve_examples", retrieve_examples_node)
    graph.add_node("generate_sql", generate_sql_node)
    graph.add_node("execute_sql", execute_sql_node)
    graph.add_node("repair_sql", repair_sql_node)
    graph.add_node("generate_report", generate_report_node)
    graph.add_node("fail", fail_node)

    graph.set_entry_point("retrieve_examples")

    graph.add_edge("retrieve_examples", "generate_sql")
    graph.add_edge("generate_sql", "execute_sql")

    graph.add_conditional_edges(
        "execute_sql",
        route_after_execute,
        {
            "generate_report": "generate_report",
            "repair_sql": "repair_sql",
            "fail": "fail",
        },
    )

    graph.add_edge("repair_sql", "execute_sql")
    graph.add_edge("generate_report", END)
    graph.add_edge("fail", END)

    return graph.compile()