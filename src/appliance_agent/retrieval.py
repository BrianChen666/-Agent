from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable

from appliance_agent.models import Chunk, RetrievedDoc
from appliance_agent.text import normalize_code, tokenize


class HybridRetriever:
    def __init__(self, chunks: Iterable[Chunk]):
        self.chunks = list(chunks)
        self._doc_tokens = {chunk.doc_id: tokenize(chunk.text) for chunk in self.chunks}
        self._doc_token_sets = {doc_id: set(tokens) for doc_id, tokens in self._doc_tokens.items()}
        self._idf = self._build_idf()

    def hybrid_search(
        self,
        query: str,
        *,
        model: str | None = None,
        fault_code: str | None = None,
        source_types: list[str] | None = None,
        dense_k: int = 20,
        sparse_k: int = 20,
        rrf_k: int = 60,
        top_k: int = 5,
    ) -> list[RetrievedDoc]:
        candidates = [
            chunk
            for chunk in self.chunks
            if self._matches_filters(chunk, model=model, fault_code=fault_code, source_types=source_types)
        ]
        if not candidates:
            return []

        query_tokens = tokenize(query)
        sparse_ranked = self._rank_sparse(candidates, query_tokens)[:sparse_k]
        dense_ranked = self._rank_dense(candidates, query_tokens)[:dense_k]

        fused: dict[str, float] = {}
        by_id = {chunk.doc_id: chunk for chunk in candidates}
        for ranked in (sparse_ranked, dense_ranked):
            for rank, chunk in enumerate(ranked, start=1):
                fused[chunk.doc_id] = fused.get(chunk.doc_id, 0.0) + 1.0 / (rrf_k + rank)

        for chunk in candidates:
            fused[chunk.doc_id] = fused.get(chunk.doc_id, 0.0) + self._metadata_boost(
                chunk, query=query, model=model, fault_code=fault_code
            )

        ranked_ids = sorted(fused, key=lambda doc_id: fused[doc_id], reverse=True)
        return [
            RetrievedDoc(
                doc_id=doc_id,
                text=by_id[doc_id].text,
                metadata=by_id[doc_id].metadata,
                score=round(fused[doc_id], 6),
            )
            for doc_id in ranked_ids[:top_k]
        ]

    def search_faq(self, query: str, *, model: str | None = None, top_k: int = 5) -> list[RetrievedDoc]:
        return self.hybrid_search(query, model=model, source_types=["faq"], top_k=top_k)

    def search_fault_code(
        self,
        query: str,
        *,
        model: str | None = None,
        fault_code: str | None = None,
        top_k: int = 5,
    ) -> list[RetrievedDoc]:
        return self.hybrid_search(
            query,
            model=model,
            fault_code=fault_code,
            source_types=["fault_code", "ref"],
            top_k=top_k,
        )

    def search_manual(self, query: str, *, model: str | None = None, top_k: int = 5) -> list[RetrievedDoc]:
        return self.hybrid_search(query, model=model, source_types=["manual"], top_k=top_k)

    def search_policy(self, query: str, *, model: str | None = None, top_k: int = 5) -> list[RetrievedDoc]:
        return self.hybrid_search(query, model=model, source_types=["policy", "fee"], top_k=top_k)

    def search_tickets(self, query: str, *, model: str | None = None, top_k: int = 5) -> list[RetrievedDoc]:
        return self.hybrid_search(query, model=model, source_types=["ticket"], top_k=top_k)

    def _build_idf(self) -> dict[str, float]:
        total = max(len(self.chunks), 1)
        doc_freq: Counter[str] = Counter()
        for tokens in self._doc_token_sets.values():
            doc_freq.update(tokens)
        return {token: math.log((1 + total) / (1 + freq)) + 1 for token, freq in doc_freq.items()}

    def _rank_sparse(self, candidates: list[Chunk], query_tokens: list[str]) -> list[Chunk]:
        query_counter = Counter(query_tokens)

        def score(chunk: Chunk) -> float:
            doc_counter = Counter(self._doc_tokens[chunk.doc_id])
            return sum(doc_counter[token] * weight * self._idf.get(token, 1.0) for token, weight in query_counter.items())

        return sorted(candidates, key=score, reverse=True)

    def _rank_dense(self, candidates: list[Chunk], query_tokens: list[str]) -> list[Chunk]:
        query_set = set(query_tokens)

        def score(chunk: Chunk) -> float:
            doc_set = self._doc_token_sets[chunk.doc_id]
            if not query_set or not doc_set:
                return 0.0
            overlap = len(query_set & doc_set)
            return overlap / math.sqrt(len(query_set) * len(doc_set))

        return sorted(candidates, key=score, reverse=True)

    def _matches_filters(
        self,
        chunk: Chunk,
        *,
        model: str | None,
        fault_code: str | None,
        source_types: list[str] | None,
    ) -> bool:
        metadata = chunk.metadata
        if source_types and metadata["source_type"] not in source_types:
            return False
        if model and model.upper() not in {value.upper() for value in metadata.get("model", [])}:
            return False
        code = normalize_code(fault_code)
        if code:
            metadata_code = normalize_code(metadata.get("fault_code"))
            if metadata_code == code:
                return True
            return code in chunk.text.upper()
        return True

    def _metadata_boost(self, chunk: Chunk, *, query: str, model: str | None, fault_code: str | None) -> float:
        boost = 0.0
        query_upper = query.upper()
        source_type = chunk.metadata["source_type"]
        code = normalize_code(fault_code)
        if code and chunk.metadata.get("fault_code") == code:
            boost += 1.0
        if code and chunk.doc_id == f"FC-{code}":
            boost += 2.0
        if model and model.upper() in {value.upper() for value in chunk.metadata.get("model", [])}:
            boost += 0.2
        if source_type == "policy" and any(word in query for word in ["保修", "免费", "三年", "凭证"]):
            boost += 0.4
        if source_type == "fee" and any(word in query for word in ["收费", "费用", "多少钱", "免费"]):
            boost += 0.4
        if "排水泵" in query and "排水泵" in chunk.text:
            boost += 0.3
        if "E2" in query_upper and "E2" in chunk.text.upper():
            boost += 0.3
        return boost
