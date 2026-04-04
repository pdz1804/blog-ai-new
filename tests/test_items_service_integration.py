from __future__ import annotations

import os
from typing import Any

import httpx
import pytest

SEED_SOURCE = "integration_seed_v1"

TEST_ITEMS: list[dict[str, Any]] = [
    {
        "title": "Transformers and Attention for Sequence Modeling",
        "abstraction": "A practical overview of self-attention and transformer blocks in modern NLP systems.",
        "description": (
            "This item explains how multi-head self-attention replaces recurrent recurrence for sequence modeling. "
            "It covers positional encoding, encoder-decoder structure, and why parallelization improves training speed. "
            "The article also contrasts full attention complexity with sparse and linear variants used in production-scale language systems."
        ),
        "tags": ["machine-learning", "nlp", "transformers", "attention"],
        "author_id": "author-ml-001",
        "author_name": "Ada Nguyen",
        "source": SEED_SOURCE,
        "url": "https://example.org/ml/transformers-attention",
        "citations": [
            "https://arxiv.org/abs/1706.03762",
            "https://arxiv.org/abs/2005.14165",
        ],
    },
    {
        "title": "Backpropagation Intuition with Computational Graphs",
        "abstraction": "Gradient flow and chain rule intuition for deep neural network training.",
        "description": (
            "This entry describes reverse-mode automatic differentiation through computational graphs. "
            "It demonstrates local derivatives, gradient accumulation, and why exploding or vanishing gradients occur in deep models. "
            "Practical notes include initialization strategies, residual connections, and normalization techniques."
        ),
        "tags": ["machine-learning", "deep-learning", "optimization"],
        "author_id": "author-ml-002",
        "author_name": "Linh Tran",
        "source": SEED_SOURCE,
        "url": "https://example.org/ml/backprop-intuition",
        "citations": ["https://www.deeplearningbook.org/"],
    },
    {
        "title": "Graph Algorithms: Dijkstra, A*, and Heuristic Design",
        "abstraction": "Shortest-path foundations and admissible heuristic design.",
        "description": (
            "A comparison of classic shortest-path algorithms with implementation notes for road networks and game maps. "
            "The document discusses priority queue choices, complexity trade-offs, and heuristic admissibility/consistency for A*. "
            "It also includes common failure modes when edge weights are dynamic or partially observed."
        ),
        "tags": ["computer-science", "algorithms", "graphs"],
        "author_id": "author-cs-001",
        "author_name": "Bao Pham",
        "source": SEED_SOURCE,
        "url": "https://example.org/cs/graph-search",
        "citations": ["https://en.wikipedia.org/wiki/A*_search_algorithm"],
    },
    {
        "title": "Distributed Systems: Consensus under Network Partitions",
        "abstraction": "Trade-offs between consistency, availability, and partition tolerance.",
        "description": (
            "This item summarizes the behavior of Raft-style replicated logs during leader election and partition events. "
            "It explains quorum, log matching, and the cost of commit latency under high tail network jitter. "
            "Operational guidance includes metrics for leader churn and safe rolling upgrades."
        ),
        "tags": ["computer-science", "distributed-systems", "raft"],
        "author_id": "author-cs-002",
        "author_name": "Minh Ho",
        "source": SEED_SOURCE,
        "url": "https://example.org/cs/consensus-partitions",
        "citations": ["https://raft.github.io/"],
    },
    {
        "title": "Reinforcement Learning with Policy Gradient Methods",
        "abstraction": "Policy optimization under stochastic trajectories.",
        "description": (
            "The article introduces REINFORCE and actor-critic approaches, emphasizing variance reduction via baselines. "
            "It clarifies the role of entropy regularization for exploration and trust-region style updates for stability. "
            "A final section maps RL concepts to recommendation and robotics workflows."
        ),
        "tags": ["machine-learning", "reinforcement-learning"],
        "author_id": "author-ml-003",
        "author_name": "Thao Vu",
        "source": SEED_SOURCE,
        "url": "https://example.org/ml/policy-gradients",
        "citations": ["https://spinningup.openai.com/"],
    },
    {
        "title": "Database Indexing: B-Tree, LSM Tree, and Workload Patterns",
        "abstraction": "Storage engine index choices for read-heavy and write-heavy systems.",
        "description": (
            "This entry compares B-Tree and LSM-tree internals, including compaction and write amplification behavior. "
            "It discusses secondary index maintenance cost, range scan performance, and memory pressure under burst writes. "
            "Practical examples include OLTP metadata stores and event ingestion pipelines."
        ),
        "tags": ["computer-science", "databases", "storage"],
        "author_id": "author-cs-003",
        "author_name": "Khanh Le",
        "source": SEED_SOURCE,
        "url": "https://example.org/cs/database-indexing",
        "citations": ["https://www.cockroachlabs.com/blog/lsm-vs-btree/"],
    },
    {
        "title": "Compiler Design: Parsing, ASTs, and Intermediate Representation",
        "abstraction": "From lexical analysis to optimization-friendly IR.",
        "description": (
            "A walkthrough of lexer and parser pipeline construction, then AST lowering into SSA-like intermediate representation. "
            "It highlights type checking passes, control-flow graph generation, and dead code elimination as baseline optimizations. "
            "The item ends with practical notes for debugging compiler pipelines with source maps."
        ),
        "tags": ["computer-science", "compilers", "programming-languages"],
        "author_id": "author-cs-004",
        "author_name": "Quang Do",
        "source": SEED_SOURCE,
        "url": "https://example.org/cs/compiler-design",
        "citations": ["https://llvm.org/docs/"],
    },
    {
        "title": "Large Language Model Evaluation and Hallucination Analysis",
        "abstraction": "Evaluation strategies for factuality, grounding, and robustness.",
        "description": (
            "This item covers benchmark design for retrieval-augmented generation and long-context QA workloads. "
            "It discusses precision/recall trade-offs in retrieval layers, citation faithfulness checks, and failure taxonomies for hallucinations. "
            "A final section outlines monitoring metrics for production LLM systems."
        ),
        "tags": ["machine-learning", "llm", "evaluation", "retrieval"],
        "author_id": "author-ml-004",
        "author_name": "Trang Bui",
        "source": SEED_SOURCE,
        "url": "https://example.org/ml/llm-eval-hallucination",
        "citations": ["https://arxiv.org/abs/2207.00032"],
    },
]


@pytest.fixture(scope="module")
def base_url() -> str:
    value = os.getenv("ITEMS_SERVICE_BASE_URL", "").strip().rstrip("/")
    if not value:
        pytest.skip("Set ITEMS_SERVICE_BASE_URL to run integration tests against deployed service")
    return value


@pytest.fixture(scope="module")
def client(base_url: str):
    with httpx.Client(base_url=base_url, timeout=30.0) as c:
        yield c


def _create_item(client: httpx.Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/api/v1/items", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_items_service_full_flow_keep_seed_data(client: httpx.Client):
    created: list[dict[str, Any]] = []

    for payload in TEST_ITEMS:
        created_item = _create_item(client, payload)
        created.append(created_item)

    assert len(created) == len(TEST_ITEMS)

    # Update one meaningful item.
    target = next(item for item in created if "Transformers" in item["title"])
    update_response = client.patch(
        f"/api/v1/items/{target['id']}",
        json={
            "title": "Transformers and Attention for Modern NLP Systems",
            "abstraction": "Updated abstraction: attention mechanisms, scaling laws, and deployment trade-offs.",
            "description": "Updated long description: includes efficient attention kernels and production latency trade-offs.",
        },
    )
    assert update_response.status_code == 200, update_response.text
    updated_item = update_response.json()
    assert "Modern NLP Systems" in updated_item["title"]

    # Delete two items to validate remove behavior.
    to_delete = [
        next(item for item in created if "Compiler Design" in item["title"]),
        next(item for item in created if "Database Indexing" in item["title"]),
    ]
    for item in to_delete:
        delete_response = client.delete(f"/api/v1/items/{item['id']}")
        assert delete_response.status_code == 200, delete_response.text

    # Verify listing still includes most seeded data and excludes deleted data.
    list_response = client.get("/api/v1/items", params={"limit": 200})
    assert list_response.status_code == 200, list_response.text
    listed = list_response.json()
    listed_ids = {row["id"] for row in listed}

    assert target["id"] in listed_ids
    for item in to_delete:
        assert item["id"] not in listed_ids

    # Fuzzy search should find ML/NLP topics with the combined relevance+freshness ranking.
    fuzzy_response = client.get(
        "/api/v1/items/search/fuzzy",
        params={"q": "transformer attention sequence modeling NLP", "limit": 5},
    )
    assert fuzzy_response.status_code == 200, fuzzy_response.text
    fuzzy_rows = fuzzy_response.json()
    assert len(fuzzy_rows) >= 1
    top = fuzzy_rows[0]["item"]
    assert "transform" in top["title"].lower()

    # Keep seeded data in the service for manual testing later.
    # Cleanup is intentionally not performed by this integration test.
