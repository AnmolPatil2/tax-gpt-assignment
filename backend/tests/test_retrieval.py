import pytest
from unittest.mock import patch, MagicMock


class TestQueryRouter:
    def test_heuristic_structured(self):
        from app.retrieval.query_router import _heuristic_classify

        q = "What is the average tax rate for corporations in Texas?"
        assert _heuristic_classify(q) == "structured"

    def test_heuristic_semantic(self):
        from app.retrieval.query_router import _heuristic_classify

        q = "How do I determine my filing status?"
        assert _heuristic_classify(q) == "semantic"

    def test_heuristic_hybrid(self):
        from app.retrieval.query_router import _heuristic_classify

        q = "What deductions do individuals in CA typically claim and how do they work?"
        assert _heuristic_classify(q) == "hybrid"

    def test_heuristic_fallback(self):
        from app.retrieval.query_router import _heuristic_classify

        q = "hello"
        result = _heuristic_classify(q)
        assert result in ("structured", "semantic", "hybrid")


class TestHybridRetrieval:
    def test_format_graph_results_with_error(self):
        from app.retrieval.hybrid import _format_graph_results

        result = _format_graph_results({"error": "connection failed"})
        assert "error" in result.lower()

    def test_format_graph_results_empty(self):
        from app.retrieval.hybrid import _format_graph_results

        result = _format_graph_results({"results": [], "error": None})
        assert "no results" in result.lower()

    def test_format_graph_results_with_data(self):
        from app.retrieval.hybrid import _format_graph_results

        data = {
            "cypher": "MATCH (n) RETURN count(n)",
            "results": [{"count": 100}],
            "error": None,
        }
        result = _format_graph_results(data)
        assert "100" in result
        assert "MATCH" in result

    def test_format_vector_results_empty(self):
        from app.retrieval.hybrid import _format_vector_results

        result = _format_vector_results([])
        assert "no relevant" in result.lower()

    def test_format_vector_results_with_docs(self):
        from app.retrieval.hybrid import _format_vector_results

        docs = [
            {
                "content": "Test content about taxes",
                "metadata": {"document": "test.pdf", "source_type": "pdf"},
                "relevance_score": 0.85,
            }
        ]
        result = _format_vector_results(docs)
        assert "test.pdf" in result
        assert "Test content" in result

    def test_build_sources(self):
        from app.retrieval.hybrid import _build_sources

        vector_docs = [
            {
                "content": "Tax info",
                "metadata": {"source_type": "pdf", "document": "form.pdf"},
                "relevance_score": 0.9,
            }
        ]
        graph_data = {
            "results": [{"avg_rate": 0.22}],
            "cypher": "MATCH (n) RETURN n",
            "error": None,
        }
        sources = _build_sources(vector_docs, graph_data)
        assert len(sources) == 2
        assert sources[0]["source_type"] == "pdf"
        assert sources[1]["source_type"] == "graph_query"
