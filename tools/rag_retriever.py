import os
from typing import Dict
import faiss
import pickle
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from core import BaseTool, get_embeddings


class RAGRetrieverTool(BaseTool):
    """
    RAG 기반 문서 검색 도구
    MCP Tool Protocol을 통해 외부 문서 검색 및 청크 기반 정보 제공
    """

    def __init__(self, index_path: str = "faiss/index", docs_path: str = "docs"):
        self.index_path = index_path
        self.docs_path = docs_path
        self.embeddings = get_embeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        self.index = None
        self.documents = []
        self._load_or_create_index()

    def _load_or_create_index(self):
        """FAISS 인덱스를 로드하거나 새로 생성"""
        try:
            # 기존 인덱스 로드 시도
            if os.path.exists(f"{self.index_path}.faiss") and os.path.exists(
                f"{self.index_path}.pkl"
            ):
                self.index = faiss.read_index(f"{self.index_path}.faiss")
                with open(f"{self.index_path}.pkl", "rb") as f:
                    self.documents = pickle.load(f)
                print(f"기존 인덱스 로드 완료: {len(self.documents)} 문서")
            else:
                # 새 인덱스 생성
                self._create_index()
        except Exception as e:
            print(f"인덱스 로드 실패, 새로 생성: {e}")
            self._create_index()

    def _create_index(self):
        """새로운 FAISS 인덱스 생성"""
        if not os.path.exists(self.docs_path):
            print(f"문서 경로가 존재하지 않습니다: {self.docs_path}")
            return

        all_chunks = []

        # PDF 파일들을 로드하고 청킹
        for filename in os.listdir(self.docs_path):
            if filename.endswith(".pdf"):
                filepath = os.path.join(self.docs_path, filename)
                loader = PyPDFLoader(filepath)
                documents = loader.load()

                # 텍스트 청킹
                chunks = self.text_splitter.split_documents(documents)
                all_chunks.extend(chunks)

        if not all_chunks:
            print("처리할 문서가 없습니다.")
            return

        # 임베딩 생성
        texts = [chunk.page_content for chunk in all_chunks]
        embeddings_list = self.embeddings.embed_documents(texts)

        # FAISS 인덱스 생성
        dimension = len(embeddings_list[0])
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings_list)

        # 문서 메타데이터 저장
        self.documents = [
            {
                "content": chunk.page_content,
                "metadata": chunk.metadata,
                "source": chunk.metadata.get("source", "unknown"),
            }
            for chunk in all_chunks
        ]

        # 인덱스 저장
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, f"{self.index_path}.faiss")
        with open(f"{self.index_path}.pkl", "wb") as f:
            pickle.dump(self.documents, f)

        print(f"새 인덱스 생성 완료: {len(self.documents)} 청크")

    def run(self, inputs: Dict) -> Dict:
        """
        MCP Tool Protocol을 통한 검색 실행

        Args:
            inputs (Dict): {"query": str, "top_k": int}

        Returns:
            Dict: {"results": List[Dict], "mcp_context": Dict}
        """
        query = inputs.get("query", "")
        top_k = inputs.get("top_k", 5)

        if not query:
            return {
                "results": [],
                "mcp_context": {
                    "role": "retriever",
                    "status": "error",
                    "message": "검색어가 없습니다.",
                },
            }

        if not self.index or len(self.documents) == 0:
            return {
                "results": [],
                "mcp_context": {
                    "role": "retriever",
                    "status": "error",
                    "message": "인덱스가 준비되지 않았습니다.",
                },
            }

        try:
            # 쿼리 임베딩
            query_embedding = self.embeddings.embed_query(query)

            # 검색 실행
            distances, indices = self.index.search([query_embedding], top_k)

            # 결과 구성
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    results.append(
                        {
                            "content": doc["content"],
                            "source": doc["source"],
                            "relevance_score": float(
                                1 / (1 + distances[0][i])
                            ),  # 거리를 관련성 점수로 변환
                            "metadata": doc["metadata"],
                        }
                    )

            return {
                "results": results,
                "mcp_context": {
                    "role": "retriever",
                    "status": "success",
                    "query": query,
                    "total_results": len(results),
                    "search_method": "semantic_similarity",
                },
            }

        except Exception as e:
            return {
                "results": [],
                "mcp_context": {
                    "role": "retriever",
                    "status": "error",
                    "message": f"검색 중 오류: {str(e)}",
                },
            }
