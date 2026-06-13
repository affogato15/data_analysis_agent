from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv

from app.agent_graph import build_agent_graph
from app.feedback import FeedbackCollector
from app.user_preferences import UserPreferencesStore
from app.saved_reports import SavedReportsStore


def load_config(base_dir: Path) -> dict:
    config_path = base_dir / "app" / "config.yaml"

    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def print_result(result: dict) -> None:
    print("\nRETRIEVED EXAMPLES:")
    for ex in result.get("golden_examples", []):
        print(f"- {ex['id']}")

    print("\nSQL:")
    print(result.get("sql", ""))

    print("\nREPORT:")
    print(result.get("report", ""))


def collect_feedback(
    question: str,
    result: dict,
    feedback_collector: FeedbackCollector,
) -> None:
    feedback = input("\nWas this answer useful? [y/n]: ").strip().lower()

    if feedback == "y" and result.get("status") == "report_generated":
        feedback_collector.save_candidate_trio(
            question=question,
            sql=result["sql"],
            report=result["report"],
            retrieved_examples=result["golden_examples"],
            user_feedback=feedback,
            metadata={
                "repair_attempts": result.get("attempt", 0),
                "rows_returned": len(result["df"]) if "df" in result else None,
            },
        )

        print("Saved as candidate trio for analyst review.")

    elif feedback == "y":
        print("Positive feedback recorded, but failed runs are not promoted to candidate trios.")

    else:
        print("Feedback skipped.")




def main() -> None:
    load_dotenv()

    base_dir = Path(__file__).resolve().parent.parent
    config = load_config(base_dir)

    agent = build_agent_graph(base_dir)

    preferences_store = UserPreferencesStore(
                                                base_dir / config["paths"]["user_preferences"]
                                            )

    feedback_collector = FeedbackCollector(
                                                base_dir / config["paths"]["candidate_trios"]
                                            )

    saved_reports_store = SavedReportsStore(
                                                base_dir / config["paths"]["saved_reports"]
                                            )

    EXIT_COMMANDS = {"exit", "quit", "q"}
    print("Retail Analytics Agent")
    print("Type 'exit', 'quit' or 'q' to quit.\n")

    user_id = input("User ID: ").strip() or "default_user"
    user_preferences = preferences_store.get_preferences(user_id)
    print(user_preferences)

    while True:
        question = input("Question: ").strip()

        if question.lower() in EXIT_COMMANDS:
            print("See you later! :)")
            break

        if len(question) < 3:
            print("Please enter a longer question.")
            continue

        if not question:
            continue

        result = agent.invoke(
            {
                "question": question,
                "user_id": user_id,
                "user_preferences": user_preferences,
            }
        )

        print_result(result)

        collect_feedback(
            question=question,
            result=result,
            feedback_collector=feedback_collector,
        )

        print("\n" + "-" * 80 + "\n")

        if result.get("status") == "report_generated":
            save_answer = input("\nSave this report? [y/n]: ").strip().lower()

            if save_answer == "y":
                report_id = saved_reports_store.save_report(
                    user_id=user_id,
                    question=question,
                    sql=result["sql"],
                    report=result["report"],
                    metadata={
                        "repair_attempts": result.get("attempt", 0),
                        "rows_returned": len(result["df"]) if "df" in result else None,
                        "retrieved_examples": [
                            ex["id"] for ex in result.get("golden_examples", [])
                        ],
                    },
                )

                print(f"Saved report ID: {report_id}")


if __name__ == "__main__":
    main()