from __future__ import annotations

import pandas as pd
from google.cloud import bigquery
from pathlib import Path
import yaml

class BigQueryExecutor:
    def __init__(
        self,
        project_id: str,
        max_bytes_billed: int,
    ):
        self.client = bigquery.Client(project=project_id)
        self.max_bytes_billed = max_bytes_billed

    def estimate_query_size(self, sql: str) -> int:
        """
        Returns estimated bytes processed without executing the query.
        """

        dry_run_config = bigquery.QueryJobConfig(
            dry_run=True,
            use_query_cache=False,
        )

        job = self.client.query(
            sql,
            job_config=dry_run_config,
        )

        return job.total_bytes_processed

    def execute_query(self, sql: str) -> pd.DataFrame:

        estimated_bytes = self.estimate_query_size(sql)

        if estimated_bytes > self.max_bytes_billed:
            raise ValueError(
                f"Query exceeds limit. "
                f"Estimated: {estimated_bytes / 1024**2:.2f} MB. "
                f"Limit: {self.max_bytes_billed / 1024**2:.2f} MB."
            )

        query_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=self.max_bytes_billed,
            use_query_cache=True,
        )

        job = self.client.query(
            sql,
            job_config=query_config,
        )

        return job.to_dataframe()

    def get_schema(self, table_id: str) -> list[dict]:

        table = self.client.get_table(table_id)

        return [
            {
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,
            }
            for field in table.schema
        ]


if __name__ == "__main__":
    config = yaml.safe_load(Path("./config.yaml").read_text())
    executor = BigQueryExecutor(project_id=config["project_id"], max_bytes_billed=config["max_bytes_billed"])
    sql = """
            SELECT *
            FROM `bigquery-public-data.thelook_ecommerce.users` 
            LIMIT 10;
        """

    df = executor.execute_query(sql)
    print(df)