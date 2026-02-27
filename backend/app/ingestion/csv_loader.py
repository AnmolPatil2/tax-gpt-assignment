from __future__ import annotations

import pandas as pd
import logging
from pathlib import Path

from app.retrieval import vector_store, graph_store

logger = logging.getLogger(__name__)


def _row_to_text(row: pd.Series) -> str:
    return (
        f"{row['Taxpayer Type']} in {row['State']} ({row['Tax Year']}): "
        f"Income ${row['Income']:,.2f} from {row['Income Source']}, "
        f"Deductions ${row['Deductions']:,.2f} ({row['Deduction Type']}), "
        f"Taxable Income ${row['Taxable Income']:,.2f}, "
        f"Tax Rate {row['Tax Rate']:.2%}, Tax Owed ${row['Tax Owed']:,.2f}"
    )


def _row_to_graph_dict(row: pd.Series) -> dict:
    return {
        "taxpayer_type": row["Taxpayer Type"],
        "state": row["State"],
        "income_source": row["Income Source"],
        "deduction_type": row["Deduction Type"],
        "tax_year": int(row["Tax Year"]),
        "income": float(row["Income"]),
        "deductions": float(row["Deductions"]),
        "taxable_income": float(row["Taxable Income"]),
        "tax_rate": float(row["Tax Rate"]),
        "tax_owed": float(row["Tax Owed"]),
        "transaction_date": str(row["Transaction Date"]),
    }


def _build_aggregate_summaries(df: pd.DataFrame) -> list[tuple[str, dict]]:
    """Build aggregate summaries per (TaxpayerType, State) for richer vector search."""
    summaries = []
    for (tp, state), group in df.groupby(["Taxpayer Type", "State"]):
        text = (
            f"Summary for {tp} taxpayers in {state}: "
            f"{len(group)} transactions, "
            f"Average income ${group['Income'].mean():,.2f}, "
            f"Average deductions ${group['Deductions'].mean():,.2f}, "
            f"Average taxable income ${group['Taxable Income'].mean():,.2f}, "
            f"Average tax rate {group['Tax Rate'].mean():.2%}, "
            f"Average tax owed ${group['Tax Owed'].mean():,.2f}, "
            f"Total tax owed ${group['Tax Owed'].sum():,.2f}, "
            f"Income sources: {', '.join(group['Income Source'].unique())}, "
            f"Deduction types: {', '.join(group['Deduction Type'].unique())}, "
            f"Tax years: {', '.join(map(str, sorted(group['Tax Year'].unique())))}"
        )
        meta = {
            "source_type": "csv_summary",
            "document": "tax_data.csv",
            "taxpayer_type": str(tp),
            "state": str(state),
        }
        summaries.append((text, meta))
    return summaries


def ingest(
    file_path: str | Path,
    skip_vectors: bool = False,
    skip_graph: bool = False,
) -> dict:
    file_path = Path(file_path)
    logger.info(f"Ingesting CSV: {file_path.name} (skip_vectors={skip_vectors}, skip_graph={skip_graph})")

    df = pd.read_csv(file_path)
    logger.info(f"Loaded {len(df)} rows from CSV")

    graph_count = 0
    vector_count = 0

    # --- Graph ingestion (no API calls — fast and free) ---
    if not skip_graph:
        graph_rows = [_row_to_graph_dict(row) for _, row in df.iterrows()]
        graph_count = graph_store.bulk_insert_transactions(graph_rows)
        logger.info(f"Inserted {graph_count} transactions into Neo4j")
    else:
        logger.info("Skipping graph ingestion (already loaded)")

    # --- Vector ingestion (requires OpenAI embeddings API) ---
    if not skip_vectors:
        ids = []
        texts = []
        metadatas = []
        for idx, row in df.iterrows():
            ids.append(f"csv_row_{idx}")
            texts.append(_row_to_text(row))
            metadatas.append({
                "source_type": "csv_row",
                "document": "tax_data.csv",
                "taxpayer_type": row["Taxpayer Type"],
                "state": row["State"],
                "tax_year": int(row["Tax Year"]),
                "income_source": row["Income Source"],
                "deduction_type": row["Deduction Type"],
            })

        summaries = _build_aggregate_summaries(df)
        for i, (text, meta) in enumerate(summaries):
            ids.append(f"csv_summary_{i}")
            texts.append(text)
            metadatas.append(meta)

        vector_count = vector_store.add_documents(ids, texts, metadatas)
        logger.info(f"Added {vector_count} chunks to ChromaDB from CSV")
    else:
        logger.info("Skipping vector ingestion (embeddings already loaded)")

    return {
        "rows_processed": len(df),
        "graph_nodes": graph_count,
        "vector_chunks": vector_count,
    }
