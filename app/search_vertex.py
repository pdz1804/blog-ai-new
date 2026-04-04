from google.cloud import discoveryengine_v1beta as discoveryengine


class VertexKeywordSearchClient:
    def __init__(self, project_id: str, location: str, datastore_id: str) -> None:
        self._client = discoveryengine.SearchServiceClient()
        self._serving_config = (
            f"projects/{project_id}/locations/{location}/collections/default_collection/"
            f"dataStores/{datastore_id}/servingConfigs/default_serving_config"
        )

    def search(self, query: str, page_size: int = 10) -> list[dict]:
        request = discoveryengine.SearchRequest(
            serving_config=self._serving_config,
            query=query,
            page_size=page_size,
        )

        response = self._client.search(request=request)

        results: list[dict] = []
        for index, item in enumerate(response.results, start=1):
            doc = item.document
            struct = doc.struct_data
            title = ""
            snippet = None
            vertex_score: float | None = None
            score_breakdown: dict[str, float] | None = None

            if struct:
                title = str(struct.get("title", struct.get("name", "")))
                snippet = str(struct.get("description", "")) if "description" in struct else None

            model_scores = getattr(item, "model_scores", None)
            if model_scores:
                score_breakdown = {}
                for key, value in dict(model_scores).items():
                    try:
                        score_breakdown[str(key)] = float(value)
                    except (TypeError, ValueError):
                        continue
                if score_breakdown:
                    vertex_score = max(score_breakdown.values())

            if vertex_score is None:
                # Stable fallback scoring by ranking position.
                rank_score = max(0.0, (page_size - (index - 1)) / max(page_size, 1)) * 100.0
                vertex_score = rank_score
                score_breakdown = {"rank_score": rank_score}

            results.append(
                {
                    "id": doc.id,
                    "title": title,
                    "snippet": snippet,
                    "score": vertex_score,
                    "score_breakdown": score_breakdown,
                }
            )

        return results
