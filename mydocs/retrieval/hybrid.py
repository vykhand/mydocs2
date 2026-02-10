"""Hybrid result combination: RRF and weighted sum."""

from tinystructlog import get_logger

from mydocs.retrieval.models import HybridSearchConfig

log = get_logger(__name__)


def combine_results_rrf(
    ft_results: list[dict],
    vec_results: list[dict],
    rrf_k: int = 60,
    ft_boost: float = 1.0,
    vec_boost: float = 1.0,
) -> list[dict]:
    """Combine results using Reciprocal Rank Fusion.

    score = sum(boost / (rrf_k + rank + 1)) across methods.
    """
    merged: dict[str, dict] = {}

    for rank, result in enumerate(ft_results):
        rid = result["id"]
        if rid not in merged:
            merged[rid] = {**result, "score": 0.0, "scores": {"fulltext": result.get("score", 0.0), "vector": 0.0}}
        rrf_score = ft_boost / (rrf_k + rank + 1)
        merged[rid]["score"] += rrf_score

    for rank, result in enumerate(vec_results):
        rid = result["id"]
        if rid not in merged:
            merged[rid] = {**result, "score": 0.0, "scores": {"fulltext": 0.0, "vector": result.get("score", 0.0)}}
        else:
            merged[rid]["scores"]["vector"] = result.get("score", 0.0)
        rrf_score = vec_boost / (rrf_k + rank + 1)
        merged[rid]["score"] += rrf_score

    results = sorted(merged.values(), key=lambda r: r["score"], reverse=True)
    return results


def combine_results_weighted_sum(
    ft_results: list[dict],
    vec_results: list[dict],
    weights: dict,
    ft_boost: float = 1.0,
    vec_boost: float = 1.0,
) -> list[dict]:
    """Combine results using weighted sum with min-max normalization."""
    w_ft = weights.get("fulltext", 0.5)
    w_vec = weights.get("vector", 0.5)

    def _normalize(results: list[dict]) -> list[dict]:
        if not results:
            return results
        scores = [r["score"] for r in results]
        min_s, max_s = min(scores), max(scores)
        spread = max_s - min_s
        if spread == 0:
            for r in results:
                r["score"] = 1.0
        else:
            for r in results:
                r["score"] = (r["score"] - min_s) / spread
        return results

    ft_normed = _normalize([{**r} for r in ft_results])
    vec_normed = _normalize([{**r} for r in vec_results])

    merged: dict[str, dict] = {}

    for result in ft_normed:
        rid = result["id"]
        merged[rid] = {
            **result,
            "score": w_ft * ft_boost * result["score"],
            "scores": {"fulltext": result["score"], "vector": 0.0},
        }

    for result in vec_normed:
        rid = result["id"]
        if rid in merged:
            merged[rid]["score"] += w_vec * vec_boost * result["score"]
            merged[rid]["scores"]["vector"] = result["score"]
        else:
            merged[rid] = {
                **result,
                "score": w_vec * vec_boost * result["score"],
                "scores": {"fulltext": 0.0, "vector": result["score"]},
            }

    results = sorted(merged.values(), key=lambda r: r["score"], reverse=True)
    return results


def combine_results(
    ft_results: list[dict],
    vec_results: list[dict],
    hybrid_config: HybridSearchConfig,
    ft_boost: float = 1.0,
    vec_boost: float = 1.0,
) -> list[dict]:
    """Route to the appropriate combination method."""
    if hybrid_config.combination_method == "rrf":
        return combine_results_rrf(
            ft_results, vec_results,
            rrf_k=hybrid_config.rrf_k,
            ft_boost=ft_boost,
            vec_boost=vec_boost,
        )
    elif hybrid_config.combination_method == "weighted_sum":
        return combine_results_weighted_sum(
            ft_results, vec_results,
            weights=hybrid_config.weights,
            ft_boost=ft_boost,
            vec_boost=vec_boost,
        )
    else:
        raise ValueError(f"Unknown combination method: {hybrid_config.combination_method}")
