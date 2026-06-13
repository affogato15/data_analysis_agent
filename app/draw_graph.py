from pathlib import Path
from app.agent_graph import build_agent_graph
from dotenv import load_dotenv

def draw_graph(base_dir: Path):

    agent = build_agent_graph(base_dir)
    png_bytes = agent.get_graph().draw_mermaid_png()

    output_path = base_dir / "agent_graph.png"
    output_path.parent.mkdir(exist_ok=True)

    output_path.write_bytes(png_bytes)

    print(f"Graph saved to: {output_path}")


if __name__ == "__main__":
    load_dotenv()
    BASE_DIR = Path(__file__).resolve().parent.parent
    draw_graph(BASE_DIR)