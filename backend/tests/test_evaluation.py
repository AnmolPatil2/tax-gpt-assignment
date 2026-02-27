"""
Evaluation script that runs test queries against the chatbot and uses
GPT-4o as a judge to score the quality of answers.

Usage:
    python -m pytest tests/test_evaluation.py -v -s

Requires:
    - Backend running with ingested data
    - OPENAI_API_KEY set in environment
"""
import json
import pytest
import httpx
from pathlib import Path

from app.llm.client import chat_completion


EVAL_FILE = Path(__file__).resolve().parent.parent / "evaluation" / "test_queries.json"
BACKEND_URL = "http://localhost:8000"

JUDGE_PROMPT = """You are evaluating a financial chatbot's answer quality.

Question: {question}
Expected keywords that should appear: {keywords}
Chatbot's answer: {answer}

Rate the answer on these criteria (1-5 scale each):
1. Relevance: Does the answer address the question?
2. Accuracy: Are the facts/numbers plausible and consistent?
3. Completeness: Does it cover the key aspects?
4. Clarity: Is it well-organized and easy to understand?

Respond ONLY with a JSON object:
{{"relevance": N, "accuracy": N, "completeness": N, "clarity": N, "total": N, "notes": "brief explanation"}}
where total is the average of the four scores."""


def load_eval_queries() -> list[dict]:
    with open(EVAL_FILE) as f:
        return json.load(f)


def get_chatbot_answer(question: str) -> str:
    """Call the chat endpoint and collect the full streamed response."""
    full_text = ""
    with httpx.stream(
        "POST",
        f"{BACKEND_URL}/api/chat",
        json={"message": question},
        timeout=120.0,
    ) as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                try:
                    chunk = json.loads(line[6:])
                    if chunk.get("type") == "token" and chunk.get("content"):
                        full_text += chunk["content"]
                except json.JSONDecodeError:
                    pass
    return full_text


def judge_answer(question: str, answer: str, keywords: list[str]) -> dict:
    """Use GPT-4o to judge the quality of an answer."""
    prompt = JUDGE_PROMPT.format(
        question=question,
        keywords=", ".join(keywords),
        answer=answer[:2000],
    )
    response = chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=300,
    )
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"relevance": 0, "accuracy": 0, "completeness": 0, "clarity": 0, "total": 0, "notes": "parse error"}


@pytest.fixture
def eval_queries():
    return load_eval_queries()


@pytest.mark.skipif(
    not Path(EVAL_FILE).exists(),
    reason="Evaluation file not found",
)
class TestEvaluation:
    """
    Integration tests that query the running chatbot and score responses.
    These are skipped if the backend isn't available.
    """

    def _is_backend_available(self) -> bool:
        try:
            r = httpx.get(f"{BACKEND_URL}/api/health", timeout=5.0)
            return r.status_code == 200
        except Exception:
            return False

    def test_structured_queries(self, eval_queries):
        if not self._is_backend_available():
            pytest.skip("Backend not running")

        structured = [q for q in eval_queries if q["category"] == "structured"]
        scores = []

        for q in structured[:3]:
            answer = get_chatbot_answer(q["question"])
            assert len(answer) > 10, f"Empty answer for: {q['question']}"

            score = judge_answer(q["question"], answer, q["expected_keywords"])
            scores.append(score.get("total", 0))
            print(f"\n  Q: {q['question']}")
            print(f"  Score: {score.get('total', 0)}/5 - {score.get('notes', '')}")

        avg = sum(scores) / len(scores) if scores else 0
        print(f"\n  Average structured score: {avg:.1f}/5")
        assert avg >= 2.0, f"Structured queries scoring too low: {avg}"

    def test_semantic_queries(self, eval_queries):
        if not self._is_backend_available():
            pytest.skip("Backend not running")

        semantic = [q for q in eval_queries if q["category"] == "semantic"]
        scores = []

        for q in semantic[:3]:
            answer = get_chatbot_answer(q["question"])
            assert len(answer) > 10, f"Empty answer for: {q['question']}"

            score = judge_answer(q["question"], answer, q["expected_keywords"])
            scores.append(score.get("total", 0))
            print(f"\n  Q: {q['question']}")
            print(f"  Score: {score.get('total', 0)}/5 - {score.get('notes', '')}")

        avg = sum(scores) / len(scores) if scores else 0
        print(f"\n  Average semantic score: {avg:.1f}/5")
        assert avg >= 2.0, f"Semantic queries scoring too low: {avg}"

    def test_hybrid_queries(self, eval_queries):
        if not self._is_backend_available():
            pytest.skip("Backend not running")

        hybrid = [q for q in eval_queries if q["category"] == "hybrid"]
        scores = []

        for q in hybrid[:2]:
            answer = get_chatbot_answer(q["question"])
            assert len(answer) > 10, f"Empty answer for: {q['question']}"

            score = judge_answer(q["question"], answer, q["expected_keywords"])
            scores.append(score.get("total", 0))
            print(f"\n  Q: {q['question']}")
            print(f"  Score: {score.get('total', 0)}/5 - {score.get('notes', '')}")

        avg = sum(scores) / len(scores) if scores else 0
        print(f"\n  Average hybrid score: {avg:.1f}/5")
        assert avg >= 2.0, f"Hybrid queries scoring too low: {avg}"

    def test_edge_case_out_of_scope(self, eval_queries):
        if not self._is_backend_available():
            pytest.skip("Backend not running")

        edge = [q for q in eval_queries if q["id"] == "edge_01"]
        if not edge:
            pytest.skip("Edge case query not found")

        answer = get_chatbot_answer(edge[0]["question"])
        assert len(answer) > 5, "No answer returned"
