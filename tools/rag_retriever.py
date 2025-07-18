import re
import time
import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass
import chromadb
from chromadb.config import Settings
from core import BaseTool, get_embeddings


class SearchMethod(Enum):
    """검색 방법 열거형"""

    VECTOR_ONLY = "vector_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"
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


class RAGRetrieverTool(BaseTool):
    """
    ChromaDB 기반 RAG 검색 도구
    MCP Tool Protocol을 통해 외부 문서 검색 및 청크 기반 정보 제공
    search_engine.py의 하이브리드 검색 로직 적용
    """

    def __init__(
        self,
        vectorstore_path: str = "data/vectorstore",
        # collection_name: str = "cloudregix_other_documents",
        collection_name: str = "cloudregix_documents",
        search_config: Optional[SearchConfig] = None,
    ):
        self.vectorstore_path = vectorstore_path
        self.collection_name = collection_name
        self.config = search_config or SearchConfig()

        # 로깅 설정
        self.logger = self._setup_logger()

        # ChromaDB 클라이언트 초기화
        self._init_chroma_client()

        # 임베딩 함수 설정 (settings.py에서 가져옴)
        self.embeddings = get_embeddings()

        # 도메인 특화 키워드 사전 초기화
        self._init_domain_keywords()

        # 성능 통계
        self.stats = {"total_searches": 0, "avg_search_time": 0.0, "cache_hits": 0}

        self.logger.info(f"ChromaDB RAG Retriever 초기화 완료: {collection_name}")

    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger("RAGRetrieverTool")
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
            self.client = chromadb.PersistentClient(
                path=self.vectorstore_path,
                settings=Settings(anonymized_telemetry=False),
            )
            self.collection = self.client.get_collection(self.collection_name)

            # 컬렉션 정보 확인
            count = self.collection.count()
            self.logger.info(
                f"컬렉션 '{self.collection_name}' 로드 완료: {count:,}개 문서"
            )

        except Exception as e:
            self.logger.error(f"ChromaDB 클라이언트 초기화 실패: {e}")
            raise

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

    def run(self, inputs: Dict) -> Dict:
        """
        MCP Tool Protocol을 통한 검색 실행

        Args:
            inputs (Dict): {
                "query": str,
                "top_k": int,
                "method": str,
                "filters": dict
            }

        Returns:
            Dict: {"results": List[Dict], "mcp_context": Dict}
        """
        query = inputs.get("query", "")
        top_k = inputs.get("top_k", 5)
        method_str = inputs.get("method", "adaptive")
        filters = inputs.get("filters", {})

        if not query:
            return {
                "results": [],
                "mcp_context": {
                    "role": "retriever",
                    "status": "error",
                    "message": "검색어가 없습니다.",
                },
            }

        try:
            # 검색 방법 결정
            method = SearchMethod(method_str)

            # 검색 실행
            search_result = self._search(
                query=query, method=method, max_results=top_k, filters=filters
            )

            if not search_result["success"]:
                return {
                    "results": [],
                    "mcp_context": {
                        "role": "retriever",
                        "status": "error",
                        "message": search_result.get("error", "검색 실패"),
                    },
                }

            # 결과 변환
            results = []
            for result in search_result["results"]:
                results.append(
                    {
                        "content": result["content"],
                        "source": result["metadata"].get("source_file", "unknown"),
                        "relevance_score": result["scores"]["relevance_score"],
                        "metadata": result["metadata"],
                    }
                )

            return {
                "results": results,
                "mcp_context": {
                    "role": "retriever",
                    "status": "success",
                    "query": query,
                    "total_results": len(results),
                    "search_method": method.value,
                    "execution_time": search_result["metadata"][
                        "execution_time_seconds"
                    ],
                },
            }

        except Exception as e:
            self.logger.error(f"검색 중 오류: {str(e)}")
            return {
                "results": [],
                "mcp_context": {
                    "role": "retriever",
                    "status": "error",
                    "message": f"검색 중 오류: {str(e)}",
                },
            }

    def _search(
        self,
        query: str,
        method: SearchMethod = SearchMethod.ADAPTIVE,
        max_results: Optional[int] = None,
        filters: Optional[Dict] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        통합 검색 실행 (search_engine.py 로직 적용)
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
            return 80
        elif complexity == QueryComplexity.MEDIUM:
            return 50
        else:
            return 30

    def _select_optimal_method(self, query_analysis: Dict) -> SearchMethod:
        """최적 검색 방법 선택"""
        if query_analysis["has_technical_terms"]:
            return SearchMethod.HYBRID
        elif query_analysis["complexity"] == QueryComplexity.HIGH:
            return SearchMethod.HYBRID
        elif len(query_analysis["domain_matches"]) > 2:
            return SearchMethod.HYBRID
        else:
            return SearchMethod.HYBRID

    def _vector_search(
        self, query: str, max_results: int, filters: Optional[Dict]
    ) -> List[SearchResult]:
        """벡터 검색"""
        try:
            # 쿼리를 임베딩으로 변환
            self.logger.info(f"쿼리 임베딩 생성 중: '{query}'")
            query_embedding = self.embeddings.embed_query(query)

            # ChromaDB 쿼리 실행 (임베딩 벡터 직접 사용)
            query_params = {
                "query_embeddings": [
                    query_embedding
                ],  # query_texts 대신 query_embeddings 사용
                "n_results": max_results,
                "include": ["documents", "metadatas", "distances"],
            }

            if filters:
                query_params["where"] = filters

            query_results = self.collection.query(**query_params)

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
            self.logger.info(f"키워드 검색 실행 중: '{query}'")

            # 모든 문서 가져오기 (where 파라미터는 None일 때만 제외)
            get_params = {"include": ["documents", "metadatas"]}

            if filters:
                get_params["where"] = filters

            all_results = self.collection.get(**get_params)

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
        self.logger.info(f"하이브리드 검색 실행 중: '{query}'")

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

    def _enhance_relevance_scores(
        self, query: str, results: List[SearchResult]
    ) -> List[SearchResult]:
        """관련성 점수 강화"""
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
        elif len(high_relevance) + len(medium_relevance) >= max_docs // 2:
            # 혼합 선택
            remaining = max_docs - len(high_relevance)
            selected_docs = high_relevance + medium_relevance[:remaining]
        else:
            # 모든 레벨 포함
            remaining = max_docs - len(high_relevance) - len(medium_relevance)
            selected_docs = (
                high_relevance + medium_relevance + low_relevance[:remaining]
            )

        # 순위 재설정
        for i, doc in enumerate(selected_docs):
            doc.rank = i + 1

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

        return {
            "query": query,
            "method": method.value,
            "results": result_dicts,
            "metadata": {
                "total_results": len(results),
                "execution_time_seconds": execution_time,
                "query_analysis": {
                    "complexity": query_analysis["complexity"].value,
                    "query_type": query_analysis["query_type"],
                    "domain_matches": query_analysis["domain_matches"],
                    "has_technical_terms": query_analysis["has_technical_terms"],
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
