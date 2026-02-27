from __future__ import annotations

from neo4j import GraphDatabase, Driver
from typing import Any

from app.config import settings
from app.llm.client import chat_completion
from app.llm.prompts import CYPHER_GENERATION_PROMPT


_driver: Driver | None = None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def verify_connection() -> bool:
    try:
        driver = get_driver()
        driver.verify_connectivity()
        return True
    except Exception:
        return False


def run_query(cypher: str, parameters: dict | None = None) -> list[dict[str, Any]]:
    driver = get_driver()
    with driver.session() as session:
        result = session.run(cypher, parameters or {})
        return [record.data() for record in result]


def create_constraints() -> None:
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:TaxpayerType) REQUIRE t.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:State) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (i:IncomeSource) REQUIRE i.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:DeductionType) REQUIRE d.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (y:TaxYear) REQUIRE y.year IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (doc:Document) REQUIRE doc.title IS UNIQUE",
    ]
    driver = get_driver()
    with driver.session() as session:
        for c in constraints:
            session.run(c)


def create_indexes() -> None:
    indexes = [
        "CREATE INDEX IF NOT EXISTS FOR (t:Transaction) ON (t.income)",
        "CREATE INDEX IF NOT EXISTS FOR (t:Transaction) ON (t.tax_owed)",
        "CREATE INDEX IF NOT EXISTS FOR (s:Section) ON (s.title)",
    ]
    driver = get_driver()
    with driver.session() as session:
        for idx in indexes:
            session.run(idx)


def clear_graph() -> None:
    driver = get_driver()
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


def insert_transaction(row: dict) -> None:
    cypher = """
    MERGE (tp:TaxpayerType {name: $taxpayer_type})
    MERGE (st:State {name: $state})
    MERGE (is_:IncomeSource {name: $income_source})
    MERGE (dt:DeductionType {name: $deduction_type})
    MERGE (ty:TaxYear {year: $tax_year})
    CREATE (t:Transaction {
        income: $income,
        deductions: $deductions,
        taxable_income: $taxable_income,
        tax_rate: $tax_rate,
        tax_owed: $tax_owed,
        transaction_date: $transaction_date
    })
    CREATE (t)-[:FILED_BY]->(tp)
    CREATE (t)-[:IN_STATE]->(st)
    CREATE (t)-[:INCOME_FROM]->(is_)
    CREATE (t)-[:CLAIMED_DEDUCTION]->(dt)
    CREATE (t)-[:IN_YEAR]->(ty)
    """
    driver = get_driver()
    with driver.session() as session:
        session.run(cypher, row)


def bulk_insert_transactions(rows: list[dict], batch_size: int = 500) -> int:
    cypher = """
    UNWIND $rows AS row
    MERGE (tp:TaxpayerType {name: row.taxpayer_type})
    MERGE (st:State {name: row.state})
    MERGE (is_:IncomeSource {name: row.income_source})
    MERGE (dt:DeductionType {name: row.deduction_type})
    MERGE (ty:TaxYear {year: row.tax_year})
    CREATE (t:Transaction {
        income: row.income,
        deductions: row.deductions,
        taxable_income: row.taxable_income,
        tax_rate: row.tax_rate,
        tax_owed: row.tax_owed,
        transaction_date: row.transaction_date
    })
    CREATE (t)-[:FILED_BY]->(tp)
    CREATE (t)-[:IN_STATE]->(st)
    CREATE (t)-[:INCOME_FROM]->(is_)
    CREATE (t)-[:CLAIMED_DEDUCTION]->(dt)
    CREATE (t)-[:IN_YEAR]->(ty)
    """
    driver = get_driver()
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        with driver.session() as session:
            session.run(cypher, {"rows": batch})
        total += len(batch)
    return total


def insert_document_structure(title: str, doc_type: str, sections: list[dict]) -> None:
    cypher = """
    MERGE (doc:Document {title: $title})
    SET doc.type = $doc_type
    WITH doc
    UNWIND $sections AS sec
    CREATE (s:Section {
        title: sec.title,
        page: sec.page,
        content_preview: sec.content_preview
    })
    CREATE (doc)-[:CONTAINS]->(s)
    """
    driver = get_driver()
    with driver.session() as session:
        session.run(cypher, {
            "title": title,
            "doc_type": doc_type,
            "sections": sections,
        })


def generate_and_execute_cypher(question: str) -> dict:
    prompt = CYPHER_GENERATION_PROMPT.format(question=question)
    cypher = chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=500,
    )

    cypher = cypher.strip()
    if cypher.startswith("```"):
        lines = cypher.split("\n")
        cypher = "\n".join(lines[1:-1])

    try:
        results = run_query(cypher)
        return {
            "cypher": cypher,
            "results": results,
            "error": None,
        }
    except Exception as e:
        return {
            "cypher": cypher,
            "results": [],
            "error": str(e),
        }


def get_node_count() -> int:
    result = run_query("MATCH (n) RETURN count(n) AS count")
    return result[0]["count"] if result else 0
