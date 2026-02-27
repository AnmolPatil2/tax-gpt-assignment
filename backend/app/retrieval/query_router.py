from __future__ import annotations

import logging

from app.llm.client import chat_completion
from app.llm.prompts import QUERY_ROUTER_PROMPT

logger = logging.getLogger(__name__)

VALID_STRATEGIES = {"structured", "semantic", "hybrid"}


def classify_query(question: str) -> str:
    """Use LLM to classify query into structured, semantic, or hybrid."""
    prompt = QUERY_ROUTER_PROMPT.format(question=question)

    try:
        response = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10,
        )
        strategy = response.strip().lower()
        if strategy in VALID_STRATEGIES:
            logger.info(f"Query classified as: {strategy}")
            return strategy
    except Exception as e:
        logger.warning(f"Query classification failed: {e}")

    # Fallback heuristic
    return _heuristic_classify(question)


def _heuristic_classify(question: str) -> str:
    """Rule-based fallback classifier."""
    q = question.lower()

    structured_keywords = [
        "average", "total", "sum", "count", "how many", "highest", "lowest",
        "most", "least", "compare", "comparison", "statistics", "tax rate",
        "tax owed", "income", "deduction", "by state", "by year",
        "corporation", "individual", "partnership", "trust", "non-profit",
    ]
    semantic_keywords = [
        "how do i", "what is", "explain", "define", "form 1040", "schedule",
        "filing", "irs", "regulation", "instruction", "section", "chapter",
        "rule", "requirement", "eligible", "qualify", "credit",
    ]

    structured_score = sum(1 for kw in structured_keywords if kw in q)
    semantic_score = sum(1 for kw in semantic_keywords if kw in q)

    if structured_score > 0 and semantic_score > 0:
        return "hybrid"
    if structured_score > semantic_score:
        return "structured"
    if semantic_score > structured_score:
        return "semantic"
    return "hybrid"
