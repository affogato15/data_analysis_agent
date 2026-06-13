import json
import chromadb
import yaml
from pathlib import Path
from sentence_transformers import SentenceTransformer

class GoldenRetriever:
    def __init__(
                    self,
                    golden_trios_path: str,
                    vector_store_path: str,
                    collection_name: str = "golden_trios",
                ):
        self.json_path = golden_trios_path
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

        with open(golden_trios_path, "r") as f:
            self.trios = json.load(f)

        self.trios_by_id = {
            trio["id"]: trio
            for trio in self.trios
        }

        self.client = chromadb.PersistentClient(path=vector_store_path)
        self.collection = self.client.get_or_create_collection(collection_name)

    def build_index(self) -> None:
        for trio in self.trios:
            text = f"""
                        Question:
                        {trio["question"]}
                        
                        Business Logic:
                        {trio["business_logic"]}
                        
                        Metrics:
                        {", ".join(trio["metrics"])}
                        
                        Tables:
                        {", ".join(trio["tables_used"])}
                        
                        Report:
                        {trio["report"]}
                    """

            embedding = self.embedding_model.encode(text).tolist()

            self.collection.upsert(
                                    ids=[trio["id"]],
                                    embeddings=[embedding],
                                    documents=[text],
                                    metadatas=[{
                                                    "id": trio["id"],
                                                    "question": trio["question"],
                                                    "metrics": ",".join(trio["metrics"]),
                                                    "tables_used": ",".join(trio["tables_used"]),
                                                }],
                                    )

    def retrieve(self, question: str, top_k: int = 3) -> list[dict]:
        question = question.strip()

        if len(question) < 3:
            raise ValueError("Question is too short for retrieval.")

        query_embedding = self.embedding_model.encode([question])[0].tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        ids = results["ids"][0]

        return [
            self.trios_by_id[id_]
            for id_ in ids
        ]

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent

    config_path = BASE_DIR / "app" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    golden_trios_path = BASE_DIR / config["paths"]["golden_bucket"]
    vector_store_path = BASE_DIR / config["paths"]["vector_store"]

    retriever = GoldenRetriever(
        golden_trios_path=str(golden_trios_path),
        vector_store_path=str(vector_store_path),
    )

    retriever.build_index()

    test_questions = [
        "Which customers generate the highest revenue?",
        "What products are most popular?",
        "How much revenue do we lose because of returns?",
        "Which categories are cancelled most often?",
        "How has revenue changed over time?"
    ]

    for q in test_questions:

        print(f"\nQUESTION: {q}")

        examples = retriever.retrieve(q, top_k=3)

        print("\nRETRIEVED EXAMPLES:")
        for ex in examples:
            print("-", ex["question"])