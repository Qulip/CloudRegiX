#!/usr/bin/env python3
"""
CloudRegiX Advanced Search Engine
고도화된 검색 기법을 다른 서비스에서 사용할 수 있도록 독립화한 클래스

Features:
- 하이브리드 검색 (벡터 + 키워드 + 메타데이터)
- 동적 검색 개수 조정
- 고도화된 관련성 점수 계산
- 도메인 특화 키워드 가중치
- 다층 문서 선택 전략
"""

import os
import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import chromadb
from chromadb.utils import embedding_functions


class SearchMethod(Enum):
    """검색 방법 열거형"""

    VECTOR_ONLY = "vector_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"
    MULTI_MODAL = "multi_modal"
    ADAPTIVE = "adaptive"


class QueryComplexity(Enum):
    """쿼리 복잡도"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SearchConfig:
    """검색 설정 클래스"""

    # 기본 설정
    max_results: int = 50
    min_similarity_score: float = 0.5

    # 하이브리드 검색 가중치
    vector_weight: float = 0.6
    keyword_weight: float = 0.4
    metadata_weight: float = 0.2

    # 관련성 점수 계산 가중치
    exact_match_weight: float = 0.3
    partial_match_weight: float = 0.2
    domain_keyword_weight: float = 0.4
    metadata_match_weight: float = 0.3
    content_quality_weight: float = 0.1
    recency_weight: float = 0.05
    authority_weight: float = 0.1

    # 동적 검색 개수 설정
    simple_query_results: int = 30
    medium_query_results: int = 50
    complex_query_results: int = 80


@dataclass
class SearchResult:
    """검색 결과 클래스"""

    id: str
    content: str
    metadata: Dict[str, Any]
    vector_score: float = 0.0
    keyword_score: float = 0.0
    metadata_score: float = 0.0
    relevance_score: float = 0.0
    final_score: float = 0.0
    rank: int = 0
    distance: float = 0.0


class CloudRegiXSearchEngine:
    """
    CloudRegiX 고도화된 검색 엔진
    다른 서비스에서 독립적으로 사용 가능한 클래스
    """

    def __init__(
        self,
        vectorstore_path: str,
        collection_name: str = "cloudregix_other_documents",
        embedding_config: Optional[Dict] = None,
        search_config: Optional[SearchConfig] = None,
    ):
        """
        검색 엔진 초기화

        Args:
            vectorstore_path: ChromaDB 저장 경로
            collection_name: 컬렉션 이름
            embedding_config: 임베딩 설정 (Azure OpenAI 등)
            search_config: 검색 설정
        """
        self.vectorstore_path = vectorstore_path
        self.collection_name = collection_name
        self.config = search_config or SearchConfig()

        # 로깅 설정
        self.logger = self._setup_logger()

        # ChromaDB 클라이언트 초기화
        self._init_chroma_client()

        # 임베딩 함수 설정
        self._init_embedding_function(embedding_config)

        # 도메인 특화 키워드 사전
        self._init_domain_keywords()

        # 성능 통계
        self.stats = {"total_searches": 0, "avg_search_time": 0.0, "cache_hits": 0}

        self.logger.info(f"CloudRegiX 검색 엔진 초기화 완료: {collection_name}")

    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger("CloudRegiXSearchEngine")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _init_chroma_client(self):
        """ChromaDB 클라이언트 초기화"""
        try:
            self.client = chromadb.PersistentClient(path=self.vectorstore_path)
            self.collection = self.client.get_collection(self.collection_name)

            # 컬렉션 정보 확인
            count = self.collection.count()
            self.logger.info(
                f"컬렉션 '{self.collection_name}' 로드 완료: {count:,}개 문서"
            )

        except Exception as e:
            self.logger.error(f"ChromaDB 클라이언트 초기화 실패: {e}")
            raise

    def _init_embedding_function(self, embedding_config: Optional[Dict]):
        """임베딩 함수 초기화"""
        if embedding_config:
            # Azure OpenAI 설정
            if embedding_config.get("provider") == "azure":
                from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

                self.embedding_function = OpenAIEmbeddingFunction(
                    api_key=embedding_config["api_key"],
                    api_base=embedding_config["endpoint"],
                    api_type="azure",
                    model_name=embedding_config.get("model", "text-embedding-3-small"),
                    deployment_id=embedding_config.get(
                        "deployment", "text-embedding-3-small"
                    ),
                    api_version=embedding_config.get(
                        "api_version", "2024-02-15-preview"
                    ),
                )
            # 일반 OpenAI 설정
            elif embedding_config.get("provider") == "openai":
                from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

                self.embedding_function = OpenAIEmbeddingFunction(
                    api_key=embedding_config["api_key"],
                    model_name=embedding_config.get("model", "text-embedding-3-small"),
                )
            # 로컬 모델 설정
            elif embedding_config.get("provider") == "local":
                from chromadb.utils.embedding_functions import (
                    SentenceTransformerEmbeddingFunction,
                )

                self.embedding_function = SentenceTransformerEmbeddingFunction(
                    model_name=embedding_config.get("model", "all-MiniLM-L6-v2")
                )
        else:
            # 기본값: 컬렉션의 기존 임베딩 함수 사용
            self.embedding_function = None
            self.logger.info("기존 컬렉션의 임베딩 함수 사용")

    def _init_domain_keywords(self):
        """도메인 특화 키워드 사전 초기화"""
        self.domain_keywords = {
            "금융규제": [
                "isms",
                "isms-p",
                "인증",
                "인증기준",
                "점검항목",
                "보안인증",
                "규제",
                "준수",
                "컴플라이언스",
            ],
            "클라우드": [
                "클라우드",
                "cloud",
                "aws",
                "azure",
                "gcp",
                "saas",
                "paas",
                "iaas",
            ],
            "보안": [
                "보안",
                "security",
                "암호화",
                "encryption",
                "접근제어",
                "방화벽",
                "vpn",
            ],
            "데이터보호": [
                "개인정보",
                "gdpr",
                "ccpa",
                "데이터보호",
                "프라이버시",
                "신용정보",
            ],
            "기술": [
                "api",
                "devops",
                "ci/cd",
                "컨테이너",
                "쿠버네티스",
                "마이크로서비스",
            ],
        }

        # 동의어 사전
        self.synonyms = {
            "클라우드": ["cloud", "클라우드서비스", "클라우드컴퓨팅"],
            "보안": ["security", "보안정책", "정보보호", "데이터보호"],
            "규제": ["regulation", "규정", "준수", "법령", "기준", "컴플라이언스"],
            "인증": ["authentication", "인증서", "인증방식", "인가"],
            "암호화": ["encryption", "암호화방식", "복호화", "해시"],
            "API": ["application programming interface", "웹서비스"],
            "ISMS": ["정보보호관리체계", "정보보안관리체계", "보안인증"],
        }

    def search(
        self,
        query: str,
        method: SearchMethod = SearchMethod.ADAPTIVE,
        max_results: Optional[int] = None,
        filters: Optional[Dict] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        통합 검색 실행

        Args:
            query: 검색 쿼리
            method: 검색 방법
            max_results: 최대 결과 수
            filters: 메타데이터 필터
            **kwargs: 추가 파라미터

        Returns:
            검색 결과 딕셔너리
        """
        start_time = time.time()

        try:
            self.logger.info(f"검색 시작: '{query}' (방법: {method.value})")

            # 1. 쿼리 분석
            query_analysis = self._analyze_query(query)

            # 2. 동적 검색 개수 결정
            if max_results is None:
                max_results = self._determine_search_count(query_analysis["complexity"])

            # 3. 검색 방법 결정 (적응형인 경우)
            if method == SearchMethod.ADAPTIVE:
                method = self._select_optimal_method(query_analysis)

            # 4. 검색 실행
            if method == SearchMethod.VECTOR_ONLY:
                raw_results = self._vector_search(query, max_results, filters)
            elif method == SearchMethod.KEYWORD_ONLY:
                raw_results = self._keyword_search(query, max_results, filters)
            elif method == SearchMethod.HYBRID:
                raw_results = self._hybrid_search(query, max_results, filters)
            elif method == SearchMethod.MULTI_MODAL:
                raw_results = self._multi_modal_search(query, max_results, filters)
            else:
                raw_results = self._hybrid_search(query, max_results, filters)

            # 5. 관련성 점수 재계산 및 문서 선택
            enhanced_results = self._enhance_relevance_scores(query, raw_results)
            selected_results = self._select_best_documents(
                enhanced_results, query_analysis
            )

            # 6. 최종 결과 구성
            execution_time = time.time() - start_time
            result = self._compose_final_result(
                query, method, selected_results, query_analysis, execution_time
            )

            # 7. 통계 업데이트
            self._update_stats(execution_time)

            self.logger.info(
                f"검색 완료: {len(selected_results)}개 결과 ({execution_time:.3f}초)"
            )

            return result

        except Exception as e:
            self.logger.error(f"검색 중 오류 발생: {e}")
            return self._error_result(query, str(e))

    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """쿼리 분석"""
        query_lower = query.lower()

        # 복잡도 평가
        complexity_indicators = {
            QueryComplexity.HIGH: [
                "거버넌스",
                "자동화",
                "종합",
                "체계",
                "프레임워크",
                "로드맵",
                "구현",
                "설계",
                "아키텍처",
            ],
            QueryComplexity.MEDIUM: [
                "요구사항",
                "규정",
                "준수",
                "보안",
                "인증",
                "가이드라인",
                "분석",
                "평가",
            ],
            QueryComplexity.LOW: [
                "무엇",
                "어떤",
                "언제",
                "어디서",
                "누가",
                "왜",
                "어떻게",
            ],
        }

        complexity_scores = {complexity: 0 for complexity in QueryComplexity}

        for complexity, indicators in complexity_indicators.items():
            for indicator in indicators:
                if indicator in query_lower:
                    complexity_scores[complexity] += 1

        # 가장 높은 점수의 복잡도
        max_score = max(complexity_scores.values())
        complexity = QueryComplexity.MEDIUM  # 기본값

        if max_score > 0:
            for comp, score in complexity_scores.items():
                if score == max_score:
                    complexity = comp
                    break

        # 도메인 키워드 분석
        domain_matches = {}
        for domain, keywords in self.domain_keywords.items():
            matches = [kw for kw in keywords if kw in query_lower]
            if matches:
                domain_matches[domain] = matches

        return {
            "complexity": complexity,
            "word_count": len(query.split()),
            "char_count": len(query),
            "domain_matches": domain_matches,
            "has_technical_terms": len(domain_matches) > 0,
            "query_type": self._classify_query_type(query),
        }

    def _classify_query_type(self, query: str) -> str:
        """쿼리 타입 분류"""
        query_lower = query.lower()

        if any(
            word in query_lower for word in ["무엇", "어떤", "어떻게", "what", "how"]
        ):
            return "information_retrieval"
        elif any(
            word in query_lower for word in ["규정", "준수", "인증", "compliance"]
        ):
            return "compliance_check"
        elif any(
            word in query_lower for word in ["문제", "오류", "해결", "error", "problem"]
        ):
            return "problem_solving"
        elif any(
            word in query_lower
            for word in ["비교", "차이", "구분", "compare", "difference"]
        ):
            return "comparison"
        else:
            return "general"

    def _determine_search_count(self, complexity: QueryComplexity) -> int:
        """쿼리 복잡도에 따른 검색 개수 결정"""
        if complexity == QueryComplexity.HIGH:
            return self.config.complex_query_results
        elif complexity == QueryComplexity.MEDIUM:
            return self.config.medium_query_results
        else:
            return self.config.simple_query_results

    def _select_optimal_method(self, query_analysis: Dict) -> SearchMethod:
        """최적 검색 방법 선택"""
        if query_analysis["has_technical_terms"]:
            return SearchMethod.MULTI_MODAL
        elif query_analysis["complexity"] == QueryComplexity.HIGH:
            return SearchMethod.HYBRID
        elif len(query_analysis["domain_matches"]) > 2:
            return SearchMethod.MULTI_MODAL
        else:
            return SearchMethod.HYBRID

    def _vector_search(
        self, query: str, max_results: int, filters: Optional[Dict]
    ) -> List[SearchResult]:
        """벡터 검색"""
        try:
            if self.embedding_function:
                # 쿼리 임베딩 생성
                query_embedding = self.embedding_function([query])
                query_results = self.collection.query(
                    query_embeddings=query_embedding,
                    n_results=max_results,
                    where=filters or {},
                )
            else:
                # 기존 임베딩 함수 사용
                query_results = self.collection.query(
                    query_texts=[query], n_results=max_results, where=filters or {}
                )

            results = []
            if query_results and query_results["ids"]:
                ids = query_results["ids"][0]
                documents = query_results["documents"][0]
                metadatas = query_results["metadatas"][0]
                distances = query_results["distances"][0]

                for i, doc_id in enumerate(ids):
                    vector_score = 1.0 - distances[i]  # 거리를 유사도로 변환

                    result = SearchResult(
                        id=doc_id,
                        content=documents[i],
                        metadata=metadatas[i],
                        vector_score=vector_score,
                        distance=distances[i],
                        rank=i + 1,
                    )
                    results.append(result)

            return results

        except Exception as e:
            self.logger.error(f"벡터 검색 오류: {e}")
            return []

    def _keyword_search(
        self, query: str, max_results: int, filters: Optional[Dict]
    ) -> List[SearchResult]:
        """키워드 검색"""
        try:
            # 모든 문서 가져오기
            all_results = self.collection.get(
                where=filters or {}, include=["documents", "metadatas"]
            )

            if not all_results or not all_results["documents"]:
                return []

            # 키워드 추출 및 확장
            keywords = self._extract_keywords(query)
            expanded_keywords = self._expand_keywords(keywords)

            # 키워드 매칭 점수 계산
            scored_results = []
            for i, (doc_id, document, metadata) in enumerate(
                zip(
                    all_results["ids"],
                    all_results["documents"],
                    all_results["metadatas"],
                )
            ):
                keyword_score = self._calculate_keyword_score(
                    document, expanded_keywords
                )

                if keyword_score > 0:
                    result = SearchResult(
                        id=doc_id,
                        content=document,
                        metadata=metadata,
                        keyword_score=keyword_score,
                        rank=i + 1,
                    )
                    scored_results.append(result)

            # 키워드 점수로 정렬
            scored_results.sort(key=lambda x: x.keyword_score, reverse=True)

            return scored_results[:max_results]

        except Exception as e:
            self.logger.error(f"키워드 검색 오류: {e}")
            return []

    def _hybrid_search(
        self, query: str, max_results: int, filters: Optional[Dict]
    ) -> List[SearchResult]:
        """하이브리드 검색 (벡터 + 키워드)"""
        # 벡터 검색
        vector_results = self._vector_search(query, max_results * 2, filters)

        # 키워드 검색
        keyword_results = self._keyword_search(query, max_results * 2, filters)

        # 결과 병합
        combined_results = self._merge_search_results(vector_results, keyword_results)

        # 하이브리드 점수 계산
        for result in combined_results:
            result.final_score = (
                result.vector_score * self.config.vector_weight
                + result.keyword_score * self.config.keyword_weight
            )

        # 최종 점수로 정렬
        combined_results.sort(key=lambda x: x.final_score, reverse=True)

        return combined_results[:max_results]

    def _multi_modal_search(
        self, query: str, max_results: int, filters: Optional[Dict]
    ) -> List[SearchResult]:
        """멀티모달 검색 (벡터 + 키워드 + 메타데이터)"""
        # 각각의 검색 실행
        vector_results = self._vector_search(query, max_results * 2, filters)
        keyword_results = self._keyword_search(query, max_results * 2, filters)
        metadata_results = self._metadata_search(query, max_results, filters)

        # 결과 병합
        all_results = self._merge_multi_modal_results(
            vector_results, keyword_results, metadata_results
        )

        # 멀티모달 점수 계산
        for result in all_results:
            result.final_score = (
                result.vector_score * self.config.vector_weight
                + result.keyword_score * self.config.keyword_weight
                + result.metadata_score * self.config.metadata_weight
            )

        # 정규화
        if all_results:
            max_score = max(r.final_score for r in all_results)
            if max_score > 0:
                for result in all_results:
                    result.final_score = result.final_score / max_score

        # 최종 점수로 정렬
        all_results.sort(key=lambda x: x.final_score, reverse=True)

        return all_results[:max_results]

    def _metadata_search(
        self, query: str, max_results: int, filters: Optional[Dict]
    ) -> List[SearchResult]:
        """메타데이터 검색"""
        try:
            all_results = self.collection.get(
                where=filters or {}, include=["documents", "metadatas"]
            )

            if not all_results or not all_results["documents"]:
                return []

            scored_results = []
            query_lower = query.lower()

            for i, (doc_id, document, metadata) in enumerate(
                zip(
                    all_results["ids"],
                    all_results["documents"],
                    all_results["metadatas"],
                )
            ):
                metadata_score = self._calculate_metadata_score(query_lower, metadata)

                if metadata_score > 0:
                    result = SearchResult(
                        id=doc_id,
                        content=document,
                        metadata=metadata,
                        metadata_score=metadata_score,
                        rank=i + 1,
                    )
                    scored_results.append(result)

            scored_results.sort(key=lambda x: x.metadata_score, reverse=True)
            return scored_results[:max_results]

        except Exception as e:
            self.logger.error(f"메타데이터 검색 오류: {e}")
            return []

    def _extract_keywords(self, query: str) -> List[str]:
        """키워드 추출"""
        # 불용어 제거
        stop_words = {
            "이",
            "그",
            "저",
            "것",
            "수",
            "등",
            "및",
            "또는",
            "그리고",
            "하는",
            "있는",
            "되는",
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "is",
            "are",
        }

        # 특수문자 제거 및 단어 분리
        cleaned_query = re.sub(r"[^\w\s]", " ", query)
        words = cleaned_query.split()

        # 키워드 필터링
        keywords = [word for word in words if len(word) >= 2 and word not in stop_words]

        return keywords

    def _expand_keywords(self, keywords: List[str]) -> List[str]:
        """키워드 확장 (동의어 포함)"""
        expanded = keywords.copy()

        for keyword in keywords:
            # 동의어 추가
            if keyword in self.synonyms:
                expanded.extend(self.synonyms[keyword])

        return list(set(expanded))

    def _calculate_keyword_score(self, document: str, keywords: List[str]) -> float:
        """키워드 매칭 점수 계산"""
        if not document or not keywords:
            return 0.0

        doc_lower = document.lower()
        score = 0.0

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # 정확한 매칭
            if keyword_lower in doc_lower:
                # 단어 경계 확인
                if re.search(r"\b" + re.escape(keyword_lower) + r"\b", doc_lower):
                    score += 1.0  # 완전 매칭
                else:
                    score += 0.5  # 부분 매칭

        # 정규화
        return min(score / len(keywords), 1.0) if keywords else 0.0

    def _calculate_metadata_score(self, query_lower: str, metadata: Dict) -> float:
        """메타데이터 점수 계산"""
        score = 0.0

        # 파일명 매칭
        filename = metadata.get("filename", "").lower()
        if any(term in filename for term in query_lower.split()):
            score += 0.4

        # 카테고리 매칭
        category = metadata.get("category", "").lower()
        if any(term in category for term in query_lower.split()):
            score += 0.3

        # 문서 타입 매칭
        doc_type = metadata.get("document_type", "").lower()
        if any(term in doc_type for term in query_lower.split()):
            score += 0.2

        # 도메인 매칭
        domain = metadata.get("domain", "").lower()
        if any(term in domain for term in query_lower.split()):
            score += 0.1

        return min(score, 1.0)

    def _merge_search_results(
        self, vector_results: List[SearchResult], keyword_results: List[SearchResult]
    ) -> List[SearchResult]:
        """벡터 + 키워드 검색 결과 병합"""
        # ID별 결과 매핑
        vector_map = {r.id: r for r in vector_results}
        keyword_map = {r.id: r for r in keyword_results}

        # 모든 고유 ID
        all_ids = set(vector_map.keys()) | set(keyword_map.keys())

        merged_results = []
        for doc_id in all_ids:
            vector_result = vector_map.get(doc_id)
            keyword_result = keyword_map.get(doc_id)

            if vector_result and keyword_result:
                # 두 결과 모두 존재
                result = vector_result
                result.keyword_score = keyword_result.keyword_score
            elif vector_result:
                # 벡터 결과만 존재
                result = vector_result
                result.keyword_score = 0.0
            else:
                # 키워드 결과만 존재
                result = keyword_result
                result.vector_score = 0.0

            merged_results.append(result)

        return merged_results

    def _merge_multi_modal_results(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        metadata_results: List[SearchResult],
    ) -> List[SearchResult]:
        """멀티모달 검색 결과 병합"""
        # ID별 결과 매핑
        vector_map = {r.id: r for r in vector_results}
        keyword_map = {r.id: r for r in keyword_results}
        metadata_map = {r.id: r for r in metadata_results}

        # 모든 고유 ID
        all_ids = (
            set(vector_map.keys()) | set(keyword_map.keys()) | set(metadata_map.keys())
        )

        merged_results = []
        for doc_id in all_ids:
            # 기본 결과 선택 (벡터 우선)
            base_result = (
                vector_map.get(doc_id)
                or keyword_map.get(doc_id)
                or metadata_map.get(doc_id)
            )

            if base_result:
                # 각 점수 병합
                base_result.vector_score = vector_map.get(
                    doc_id, SearchResult("", "", {})
                ).vector_score
                base_result.keyword_score = keyword_map.get(
                    doc_id, SearchResult("", "", {})
                ).keyword_score
                base_result.metadata_score = metadata_map.get(
                    doc_id, SearchResult("", "", {})
                ).metadata_score

                merged_results.append(base_result)

        return merged_results

    def _enhance_relevance_scores(
        self, query: str, results: List[SearchResult]
    ) -> List[SearchResult]:
        """관련성 점수 강화 (CloudRegiX 고유 알고리즘)"""
        if not results:
            return results

        query_lower = query.lower()
        query_words = set(query_lower.split())

        for result in results:
            content_lower = result.content.lower()
            content_words = set(content_lower.split())
            metadata = result.metadata

            relevance_score = 0.0

            # 1. 정확한 키워드 매칭 (30% 가중치)
            exact_matches = query_words & content_words
            relevance_score += len(exact_matches) * self.config.exact_match_weight

            # 2. 부분 키워드 매칭 (20% 가중치)
            for word in query_words:
                if len(word) > 2 and word in content_lower:
                    relevance_score += self.config.partial_match_weight

            # 3. 도메인 키워드 가중치 (40% 가중치)
            for domain, keywords in self.domain_keywords.items():
                if any(kw in query_lower for kw in keywords):
                    for keyword in keywords:
                        if keyword in content_lower:
                            relevance_score += self.config.domain_keyword_weight
                            break

            # 4. 메타데이터 기반 점수 (30% 가중치)
            filename = metadata.get("filename", "").lower()
            category = metadata.get("category", "").lower()

            for word in query_words:
                if len(word) > 2 and word in filename:
                    relevance_score += self.config.metadata_match_weight

            # 5. 내용 품질 점수 (10% 가중치)
            content_length = len(result.content)
            if content_length > 2000:
                relevance_score += self.config.content_quality_weight
            elif content_length > 1000:
                relevance_score += self.config.content_quality_weight * 0.5

            # 6. 최신성 점수 (5% 가중치)
            if any(year in filename for year in ["2023", "2024", "2025"]):
                relevance_score += self.config.recency_weight

            # 7. 출처 신뢰도 점수 (10% 가중치)
            authority_sources = ["금융보안원", "금융위원회", "kisa", "한국인터넷진흥원"]
            if any(source in filename for source in authority_sources):
                relevance_score += self.config.authority_weight

            # 점수 정규화 (0.0 ~ 1.0)
            result.relevance_score = min(relevance_score, 1.0)

        # 관련성 점수로 정렬
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results

    def _select_best_documents(
        self, results: List[SearchResult], query_analysis: Dict
    ) -> List[SearchResult]:
        """최적 문서 선택 전략"""
        if not results:
            return results

        # 관련성 수준별 분류
        high_relevance = [r for r in results if r.relevance_score >= 0.6]
        medium_relevance = [r for r in results if 0.4 <= r.relevance_score < 0.6]
        low_relevance = [r for r in results if 0.2 <= r.relevance_score < 0.4]

        # 쿼리 복잡도에 따른 선택 전략
        if query_analysis["complexity"] == QueryComplexity.HIGH:
            max_docs = 15
        elif query_analysis["complexity"] == QueryComplexity.MEDIUM:
            max_docs = 10
        else:
            max_docs = 5

        # 문서 선택
        selected_docs = []

        if len(high_relevance) >= max_docs // 2:
            # 고관련성 문서 우선 선택
            selected_docs = high_relevance[:max_docs]
            selection_strategy = "high_relevance_priority"
        elif len(high_relevance) + len(medium_relevance) >= max_docs // 2:
            # 혼합 선택
            remaining = max_docs - len(high_relevance)
            selected_docs = high_relevance + medium_relevance[:remaining]
            selection_strategy = "mixed_relevance"
        else:
            # 모든 레벨 포함
            remaining = max_docs - len(high_relevance) - len(medium_relevance)
            selected_docs = (
                high_relevance + medium_relevance + low_relevance[:remaining]
            )
            selection_strategy = "all_levels"

        # 순위 재설정
        for i, doc in enumerate(selected_docs):
            doc.rank = i + 1

        self.logger.info(
            f"문서 선택 전략: {selection_strategy}, 선택된 문서: {len(selected_docs)}개"
        )

        return selected_docs

    def _compose_final_result(
        self,
        query: str,
        method: SearchMethod,
        results: List[SearchResult],
        query_analysis: Dict,
        execution_time: float,
    ) -> Dict[str, Any]:
        """최종 결과 구성"""
        # 결과를 딕셔너리 형태로 변환
        result_dicts = []
        for result in results:
            result_dict = {
                "id": result.id,
                "content": result.content,
                "metadata": result.metadata,
                "scores": {
                    "vector_score": result.vector_score,
                    "keyword_score": result.keyword_score,
                    "metadata_score": result.metadata_score,
                    "relevance_score": result.relevance_score,
                    "final_score": result.final_score,
                },
                "rank": result.rank,
                "distance": result.distance,
            }
            result_dicts.append(result_dict)

        # 소스 분포 계산
        source_distribution = {}
        for result in results:
            source = result.metadata.get("source_file", "unknown")
            source_distribution[source] = source_distribution.get(source, 0) + 1

        return {
            "query": query,
            "method": method.value,
            "query_analysis": {
                "complexity": query_analysis["complexity"].value,
                "query_type": query_analysis["query_type"],
                "domain_matches": query_analysis["domain_matches"],
                "has_technical_terms": query_analysis["has_technical_terms"],
            },
            "results": result_dicts,
            "metadata": {
                "total_results": len(results),
                "execution_time_seconds": execution_time,
                "search_config": {
                    "vector_weight": self.config.vector_weight,
                    "keyword_weight": self.config.keyword_weight,
                    "metadata_weight": self.config.metadata_weight,
                },
                "source_distribution": source_distribution,
                "score_statistics": {
                    "avg_relevance": (
                        sum(r.relevance_score for r in results) / len(results)
                        if results
                        else 0.0
                    ),
                    "max_relevance": (
                        max(r.relevance_score for r in results) if results else 0.0
                    ),
                    "min_relevance": (
                        min(r.relevance_score for r in results) if results else 0.0
                    ),
                },
            },
            "success": True,
        }

    def _error_result(self, query: str, error_message: str) -> Dict[str, Any]:
        """오류 결과"""
        return {"query": query, "results": [], "error": error_message, "success": False}

    def _update_stats(self, execution_time: float):
        """통계 업데이트"""
        self.stats["total_searches"] += 1

        # 평균 응답 시간 계산
        total_time = (
            self.stats["avg_search_time"] * (self.stats["total_searches"] - 1)
            + execution_time
        )
        self.stats["avg_search_time"] = total_time / self.stats["total_searches"]

    def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        try:
            count = self.collection.count()

            # 샘플 메타데이터 조회
            sample = self.collection.peek(limit=5)
            sample_metadata_keys = []
            if sample and sample.get("metadatas"):
                sample_metadata_keys = (
                    list(sample["metadatas"][0].keys()) if sample["metadatas"] else []
                )

            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "sample_metadata_keys": sample_metadata_keys,
                "vectorstore_path": self.vectorstore_path,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_search_statistics(self) -> Dict[str, Any]:
        """검색 통계 조회"""
        return {
            "total_searches": self.stats["total_searches"],
            "average_search_time": self.stats["avg_search_time"],
            "cache_hits": self.stats["cache_hits"],
            "supported_methods": [method.value for method in SearchMethod],
            "domain_keywords_count": sum(
                len(keywords) for keywords in self.domain_keywords.values()
            ),
            "synonyms_count": len(self.synonyms),
        }


# MCP Tool용 편의 함수
def create_search_engine(
    vectorstore_path: str,
    collection_name: str = "cloudregix_other_documents",
    embedding_config: Optional[Dict] = None,
) -> CloudRegiXSearchEngine:
    """
    검색 엔진 생성 편의 함수

    Args:
        vectorstore_path: ChromaDB 저장 경로 (예: "C:/path/to/data/vectorstore")
        collection_name: 컬렉션 이름
        embedding_config: 임베딩 설정 (옵션)

    Returns:
        CloudRegiXSearchEngine 인스턴스
    """
    return CloudRegiXSearchEngine(
        vectorstore_path=vectorstore_path,
        collection_name=collection_name,
        embedding_config=embedding_config,
    )


def simple_search(
    vectorstore_path: str,
    query: str,
    collection_name: str = "cloudregix_other_documents",
    max_results: int = 10,
    method: str = "adaptive",
) -> Dict[str, Any]:
    """
    간단한 검색 함수 (MCP Tool용)

    Args:
        vectorstore_path: ChromaDB 저장 경로
        query: 검색 쿼리
        collection_name: 컬렉션 이름
        max_results: 최대 결과 수
        method: 검색 방법 ("vector_only", "keyword_only", "hybrid", "multi_modal", "adaptive")

    Returns:
        검색 결과 딕셔너리
    """
    search_engine = create_search_engine(vectorstore_path, collection_name)
    search_method = SearchMethod(method)

    return search_engine.search(
        query=query, method=search_method, max_results=max_results
    )


# 사용 예시
if __name__ == "__main__":
    # Azure OpenAI 설정 예시
    embedding_config = {
        "provider": "azure",
        "api_key": "your-api-key",
        "endpoint": "https://your-endpoint.openai.azure.com/",
        "model": "text-embedding-3-small",
        "deployment": "text-embedding-3-small",
        "api_version": "2024-02-15-preview",
    }

    # 검색 엔진 생성
    search_engine = create_search_engine(
        vectorstore_path="C:/Users/alexr/Python/data/data/vectorstore",
        collection_name="cloudregix_other_documents",
        embedding_config=embedding_config,
    )

    # 검색 실행
    result = search_engine.search(
        query="ISMS-P 인증 기준은 무엇인가요?",
        method=SearchMethod.ADAPTIVE,
        max_results=10,
    )

    # 결과 출력
    print(f"검색 결과: {result['metadata']['total_results']}개")
    print(f"실행 시간: {result['metadata']['execution_time_seconds']:.3f}초")

    for i, doc in enumerate(result["results"][:3], 1):
        print(f"\n{i}. [관련성: {doc['scores']['relevance_score']:.3f}]")
        print(f"   내용: {doc['content'][:200]}...")
        print(f"   소스: {doc['metadata'].get('source_file', 'unknown')}")
