#!/usr/bin/env python3
"""
독립적인 문서 벡터화 스크립트
클라우드 거버넌스 서비스용 문서를 벡터화하여 ChromaDB에 저장합니다.

사용법:
1. 벡터화할 문서들을 data_source/raw/ 디렉토리에 저장
2. python standalone_vectorization.py 실행

지원 파일 형식: PDF, DOCX, XLSX, TXT
"""

import os
import sys
import json
import time
import uuid
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# 프로젝트 루트 경로 설정
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 필요한 라이브러리 임포트
try:
    import chromadb
    from chromadb.types import Collection
    from chromadb.utils import embedding_functions
    import fitz  # PyMuPDF
    from docx import Document
    import pandas as pd
    from config.llm import get_embeddings
    from config.settings import Settings
    from vectorstore.stores.chroma_store import ChromaStore
except ImportError as e:
    print(f"❌ 필요한 라이브러리를 설치해주세요: {e}")
    print("pip install chromadb pymupdf python-docx pandas openpyxl")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("vectorization.log"), logging.StreamHandler()],
)
logger = logging.getLogger("VectorizationScript")


class DocumentParser:
    """문서 파싱 클래스"""

    def __init__(self):
        self.supported_extensions = {".pdf", ".docx", ".xlsx", ".xls", ".txt"}

    def parse_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """파일을 파싱하여 텍스트와 메타데이터를 추출합니다."""
        try:
            extension = file_path.suffix.lower()

            if extension == ".pdf":
                return self._parse_pdf(file_path)
            elif extension == ".docx":
                return self._parse_docx(file_path)
            elif extension in [".xlsx", ".xls"]:
                return self._parse_excel(file_path)
            elif extension == ".txt":
                return self._parse_txt(file_path)
            else:
                logger.warning(f"지원하지 않는 파일 형식: {extension}")
                return None

        except Exception as e:
            logger.error(f"파일 파싱 중 오류 발생 ({file_path}): {e}")
            return None

    def _parse_pdf(self, file_path: Path) -> Dict[str, Any]:
        """PDF 파일 파싱"""
        doc = fitz.open(str(file_path))
        text_content = ""

        for page_num in range(len(doc)):
            page = doc[page_num]
            text_content += page.get_text() + "\n"

        doc.close()

        return {
            "content": text_content.strip(),
            "metadata": {
                "file_name": file_path.name,
                "file_type": "pdf",
                "file_size": file_path.stat().st_size,
                "parsed_at": datetime.now().isoformat(),
            },
        }

    def _parse_docx(self, file_path: Path) -> Dict[str, Any]:
        """DOCX 파일 파싱"""
        doc = Document(str(file_path))
        text_content = ""

        for paragraph in doc.paragraphs:
            text_content += paragraph.text + "\n"

        return {
            "content": text_content.strip(),
            "metadata": {
                "file_name": file_path.name,
                "file_type": "docx",
                "file_size": file_path.stat().st_size,
                "parsed_at": datetime.now().isoformat(),
            },
        }

    def _parse_excel(self, file_path: Path) -> Dict[str, Any]:
        """Excel 파일 파싱"""
        df = pd.read_excel(str(file_path), sheet_name=None)
        text_content = ""

        for sheet_name, sheet_df in df.items():
            text_content += f"[시트: {sheet_name}]\n"
            text_content += sheet_df.to_string(index=False) + "\n\n"

        return {
            "content": text_content.strip(),
            "metadata": {
                "file_name": file_path.name,
                "file_type": "excel",
                "file_size": file_path.stat().st_size,
                "parsed_at": datetime.now().isoformat(),
            },
        }

    def _parse_txt(self, file_path: Path) -> Dict[str, Any]:
        """TXT 파일 파싱"""
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()

        return {
            "content": text_content.strip(),
            "metadata": {
                "file_name": file_path.name,
                "file_type": "txt",
                "file_size": file_path.stat().st_size,
                "parsed_at": datetime.now().isoformat(),
            },
        }


class DocumentChunker:
    """문서 청킹 클래스"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(
        self, content: str, metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """문서를 청크로 분할합니다."""
        if not content or len(content.strip()) == 0:
            return []

        # 문장 단위로 분할
        sentences = self._split_into_sentences(content)
        chunks = []
        current_chunk = ""
        current_size = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            # 청크 크기 초과 시 새로운 청크 생성
            if current_size + sentence_size > self.chunk_size and current_chunk:
                chunks.append(
                    {
                        "content": current_chunk.strip(),
                        "metadata": {
                            **metadata,
                            "chunk_index": len(chunks),
                            "chunk_size": len(current_chunk.strip()),
                        },
                    }
                )

                # 오버랩 처리
                if self.chunk_overlap > 0:
                    overlap_text = current_chunk[-self.chunk_overlap :]
                    current_chunk = overlap_text + " " + sentence
                    current_size = len(current_chunk)
                else:
                    current_chunk = sentence
                    current_size = sentence_size
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                current_size += sentence_size

        # 마지막 청크 추가
        if current_chunk.strip():
            chunks.append(
                {
                    "content": current_chunk.strip(),
                    "metadata": {
                        **metadata,
                        "chunk_index": len(chunks),
                        "chunk_size": len(current_chunk.strip()),
                    },
                }
            )

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """텍스트를 문장 단위로 분할합니다."""
        # 한국어와 영어 문장 분할 패턴
        sentence_endings = re.compile(r"[.!?]\s+|[。！？]\s*")
        sentences = sentence_endings.split(text)

        # 빈 문장 제거
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences


class VectorStore:
    """벡터 저장소 클래스 - config/llm.py의 get_embeddings() 사용"""

    def __init__(
        self,
        collection_name: str = "cloudregix_documents",
        persist_directory: str = "data_source/vectorstore",
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        # config/llm.py의 get_embeddings() 함수 사용
        self.embedding_model = get_embeddings()

        # 설정 정보 확인용
        self.settings = Settings()

        # ChromaDB 클라이언트 직접 초기화
        os.makedirs(persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_directory)

        # 컬렉션 생성 또는 가져오기
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

        # 임베딩 모델 정보 로깅
        logger.info(f"임베딩 설정 확인:")
        logger.info(f"  - 모델: text-embedding-3-small (config/llm.py)")
        logger.info(f"  - 차원: 1536")
        logger.info(f"  - 임베딩 함수: get_embeddings() 사용")

        logger.info(f"벡터 저장소 초기화 완료: {collection_name}")
        logger.info(f"저장 위치: {persist_directory}")

        # 기존 컬렉션 정보 확인
        self._check_existing_collection()

    def _check_existing_collection(self):
        """기존 컬렉션의 임베딩 차원을 확인합니다."""
        try:
            existing_count = self.collection.count()
            if existing_count > 0:
                logger.info(f"기존 컬렉션에 {existing_count}개의 문서가 있습니다.")

                # 기존 데이터의 첫 번째 문서를 가져와서 차원 확인
                sample_data = self.collection.get(
                    limit=1, include=["embeddings", "metadatas"]
                )

                if (
                    sample_data
                    and sample_data["embeddings"]
                    and len(sample_data["embeddings"]) > 0
                ):
                    existing_dimension = len(sample_data["embeddings"][0])
                    expected_dimension = 1536  # text-embedding-3-small의 차원

                    logger.info(f"기존 데이터 임베딩 차원: {existing_dimension}")
                    logger.info(f"현재 설정 임베딩 차원: {expected_dimension}")

                    if existing_dimension != expected_dimension:
                        logger.warning("⚠️  임베딩 차원 불일치 감지!")
                        logger.warning(
                            f"기존: {existing_dimension}차원, 현재: {expected_dimension}차원"
                        )
                        logger.warning(
                            "새로운 컬렉션 이름을 사용하거나 기존 데이터를 삭제해야 할 수 있습니다."
                        )

                        # 기존 데이터의 메타데이터에서 모델 정보 확인
                        if (
                            sample_data["metadatas"]
                            and len(sample_data["metadatas"]) > 0
                        ):
                            metadata = sample_data["metadatas"][0]
                            existing_model = metadata.get("embedding_model", "unknown")
                            logger.info(f"기존 데이터 임베딩 모델: {existing_model}")

                        # 차원 불일치 해결 방법 제시
                        self._handle_dimension_mismatch(
                            existing_dimension, expected_dimension
                        )
                    else:
                        logger.info("✅ 임베딩 차원이 일치합니다.")
                else:
                    logger.info("기존 데이터에서 임베딩 정보를 확인할 수 없습니다.")
            else:
                logger.info("새로운 컬렉션입니다.")

        except Exception as e:
            logger.warning(f"기존 컬렉션 확인 중 오류: {e}")

    def _handle_dimension_mismatch(self, existing_dim: int, expected_dim: int):
        """임베딩 차원 불일치 시 해결 방법을 제시합니다."""
        print("\n" + "=" * 60)
        print("⚠️  임베딩 차원 불일치 문제 감지")
        print("=" * 60)
        print(f"기존 벡터 데이터: {existing_dim}차원")
        print(f"현재 설정 모델: {expected_dim}차원")
        print("\n해결 방법:")
        print("1. 새로운 컬렉션 이름 사용 (권장)")
        print("2. 기존 벡터 데이터 삭제 후 재생성")
        print("3. 작업 중단")

        while True:
            choice = input("\n선택하세요 (1/2/3): ").strip()

            if choice == "1":
                # 새로운 컬렉션 이름 생성
                import time

                timestamp = int(time.time())
                new_collection_name = (
                    f"{self.collection_name}_v{expected_dim}_{timestamp}"
                )
                logger.info(f"새로운 컬렉션 이름으로 변경: {new_collection_name}")

                # 새로운 컬렉션 생성
                self.collection_name = new_collection_name
                self.collection = self.client.get_or_create_collection(
                    name=new_collection_name, metadata={"hnsw:space": "cosine"}
                )
                logger.info("새로운 컬렉션으로 진행합니다.")
                break

            elif choice == "2":
                confirm = (
                    input("⚠️  기존 데이터를 모두 삭제하시겠습니까? (yes/no): ")
                    .strip()
                    .lower()
                )
                if confirm in ["yes", "y"]:
                    try:
                        self.client.delete_collection(name=self.collection_name)
                        self.collection = self.client.get_or_create_collection(
                            name=self.collection_name, metadata={"hnsw:space": "cosine"}
                        )
                        logger.info("기존 컬렉션이 삭제되었습니다.")
                        break
                    except Exception as e:
                        logger.error(f"컬렉션 삭제 중 오류: {e}")
                        print("컬렉션 삭제에 실패했습니다. 다른 방법을 선택해주세요.")
                else:
                    print("삭제를 취소했습니다. 다른 방법을 선택해주세요.")

            elif choice == "3":
                logger.info("사용자가 작업을 중단했습니다.")
                raise SystemExit("임베딩 차원 불일치로 인해 작업을 중단합니다.")

            else:
                print("올바른 선택지를 입력해주세요 (1, 2, 또는 3).")

    def add_documents(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 1000,
        batch_delay: float = 0.5,
    ) -> bool:
        """청크들을 벡터 저장소에 추가합니다. 대용량 파일을 위한 배치 처리 지원."""
        try:
            if not chunks:
                logger.warning("추가할 청크가 없습니다.")
                return False

            total_chunks = len(chunks)
            logger.info(f"총 {total_chunks}개 청크를 처리합니다.")

            # 배치 크기 조정 (Azure OpenAI API 제한 고려)
            if total_chunks > batch_size:
                logger.info(
                    f"대용량 파일 감지: {total_chunks}개 청크를 {batch_size}개씩 배치로 처리합니다."
                )

                # 배치별로 처리
                for i in range(0, total_chunks, batch_size):
                    batch_chunks = chunks[i : i + batch_size]
                    batch_num = (i // batch_size) + 1
                    total_batches = (total_chunks + batch_size - 1) // batch_size

                    logger.info(
                        f"배치 {batch_num}/{total_batches} 처리 중... ({len(batch_chunks)}개 청크)"
                    )

                    if not self._process_batch(batch_chunks, i, batch_delay):
                        logger.error(f"배치 {batch_num} 처리 실패")
                        return False

                logger.info(f"모든 배치 처리 완료: {total_chunks}개 청크")
                return True
            else:
                # 작은 파일은 기존 방식으로 처리
                return self._process_batch(chunks, 0, batch_delay)

        except Exception as e:
            logger.error(f"벡터 저장 중 오류 발생: {e}")
            return False

    def _process_batch(
        self,
        chunks: List[Dict[str, Any]],
        start_index: int = 0,
        batch_delay: float = 0.5,
    ) -> bool:
        """청크 배치를 처리합니다."""
        try:
            # 청크 내용 추출 및 전처리
            chunk_contents = []
            for chunk in chunks:
                content = chunk["content"]
                # 텍스트 전처리 (특수 문자 및 인코딩 문제 해결)
                content = self._preprocess_text(content)
                chunk_contents.append(content)

            # 빈 내용 필터링
            valid_chunks = []
            valid_contents = []
            for i, (chunk, content) in enumerate(zip(chunks, chunk_contents)):
                if content and len(content.strip()) > 10:  # 최소 길이 확인
                    valid_chunks.append(chunk)
                    valid_contents.append(content)
                else:
                    logger.warning(f"빈 청크 건너뛰기: 인덱스 {start_index + i}")

            if not valid_chunks:
                logger.warning("유효한 청크가 없습니다.")
                return True  # 빈 청크는 성공으로 처리

            # config/llm.py의 get_embeddings()를 사용하여 임베딩 생성
            embeddings = self.embedding_model.embed_documents(valid_contents)

            # 벡터스토어에 저장할 데이터 준비
            doc_id = str(uuid.uuid4())
            ids = []
            documents = []
            metadatas = []

            for i, chunk in enumerate(valid_chunks):
                chunk_id = f"{doc_id}_chunk_{start_index + i}"
                ids.append(chunk_id)
                documents.append(valid_contents[i])

                # 기존 시스템과 동일한 메타데이터 구조
                metadata = chunk["metadata"].copy()

                # 카테고리 추출 (기존 시스템과 동일한 로직)
                source_filename = metadata.get("file_name", "")
                category = self._extract_category(source_filename)

                # 도메인 결정 (기존 시스템과 동일한 로직)
                domain = "general"
                financial_keywords = [
                    "금융",
                    "법률",
                    "신용정보",
                    "KISA",
                    "NIST",
                    "ISMS",
                ]
                if any(keyword in category for keyword in financial_keywords):
                    domain = "financial"

                metadata.update(
                    {
                        "doc_id": doc_id,
                        "chunk_id": chunk_id,
                        "chunk_index": start_index + i,
                        "source_file": source_filename,
                        "category": category,
                        "domain": domain,
                        "document_type": "chunked_other",
                        "embedded_at": datetime.now().isoformat(),
                        "chunk_size": len(valid_contents[i]),
                        "total_chunks": len(valid_chunks),
                        "embedding_model": "get_embeddings",
                        "embedding_dimension": 1536,
                    }
                )

                metadatas.append(metadata)

            # ChromaDB에 직접 저장
            self.collection.add(
                ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
            )

            # 배치 간 대기 (API 안정성을 위해)
            if batch_delay > 0:
                time.sleep(batch_delay)

            return True

        except Exception as e:
            logger.error(f"배치 처리 중 오류 발생: {e}")
            return False

    def _preprocess_text(self, text: str) -> str:
        """텍스트 전처리를 수행합니다."""
        if not text:
            return ""

        # 인코딩 문제 해결
        try:
            # 유니코드 정규화
            import unicodedata

            text = unicodedata.normalize("NFKC", text)
        except:
            pass

        # 특수 문자 처리
        import re

        # 연속된 공백 제거
        text = re.sub(r"\s+", " ", text)

        # 제어 문자 제거 (줄바꿈과 탭 제외)
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # 너무 긴 연속된 문자 제거 (스팸 방지)
        text = re.sub(r"(.)\1{50,}", r"\1" * 10, text)

        return text.strip()

    def _extract_category(self, filename: str) -> str:
        """파일명에서 카테고리를 추출합니다."""
        # [기관명] 패턴 추출
        match = re.search(r"\[([^\]]+)\]", filename)
        if match:
            return f"[{match.group(1)}]"
        return "기타"

    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계를 반환합니다."""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "persist_directory": self.persist_directory,
            }
        except Exception as e:
            logger.error(f"통계 조회 중 오류 발생: {e}")
            return {}


class VectorizationPipeline:
    """벡터화 파이프라인 클래스"""

    def __init__(
        self,
        input_dir: str = "data_source/raw",
        collection_name: str = "cloudregix_documents",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.input_dir = Path(input_dir)
        self.parser = DocumentParser()
        self.chunker = DocumentChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        self.vector_store = VectorStore(collection_name)

        # 입력 디렉토리 생성
        self.input_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"청킹 설정: 크기={chunk_size}, 오버랩={chunk_overlap}")

    def run(self) -> Dict[str, Any]:
        """전체 벡터화 파이프라인을 실행합니다."""
        logger.info("=" * 60)
        logger.info("문서 벡터화 파이프라인 시작")
        logger.info("=" * 60)

        start_time = time.time()

        # 처리할 파일 검색 (하위 디렉토리 포함)
        files = self._find_files_recursive()
        if not files:
            logger.warning(f"처리할 파일이 없습니다: {self.input_dir}")
            return {
                "status": "no_files",
                "message": f"{self.input_dir}에 처리할 파일이 없습니다.",
                "total_files": 0,
                "processed_files": 0,
                "failed_files": 0,
            }

        logger.info(f"처리할 파일 수: {len(files)}")

        # 파일별 처리
        results = {
            "total_files": len(files),
            "processed_files": 0,
            "failed_files": 0,
            "failed_file_list": [],
            "total_chunks": 0,
        }

        for file_path in files:
            try:
                logger.info(f"처리 중: {file_path.relative_to(self.input_dir)}")

                # 1. 파일 파싱
                parsed_data = self.parser.parse_file(file_path)
                if not parsed_data:
                    results["failed_files"] += 1
                    results["failed_file_list"].append(str(file_path))
                    continue

                # 2. 문서 청킹
                chunks = self.chunker.chunk_document(
                    parsed_data["content"], parsed_data["metadata"]
                )

                if not chunks:
                    logger.warning(f"청크가 생성되지 않았습니다: {file_path.name}")
                    results["failed_files"] += 1
                    results["failed_file_list"].append(str(file_path))
                    continue

                # 3. 벡터 저장 (적응형 배치 크기)
                batch_size = self._calculate_batch_size(len(chunks))
                if self.vector_store.add_documents(chunks, batch_size=batch_size):
                    results["processed_files"] += 1
                    results["total_chunks"] += len(chunks)
                    logger.info(f"완료: {file_path.name} ({len(chunks)}개 청크)")
                else:
                    results["failed_files"] += 1
                    results["failed_file_list"].append(str(file_path))

            except Exception as e:
                logger.error(f"파일 처리 중 오류 ({file_path.name}): {e}")
                results["failed_files"] += 1
                results["failed_file_list"].append(str(file_path))

        # 실행 시간 계산
        end_time = time.time()
        execution_time = end_time - start_time

        results.update(
            {
                "execution_time_seconds": execution_time,
                "vector_store_stats": self.vector_store.get_collection_stats(),
            }
        )

        # 결과 요약
        self._print_summary(results)

        return results

    def _calculate_batch_size(self, chunk_count: int) -> int:
        """청크 수에 따라 적응형 배치 크기를 계산합니다."""
        if chunk_count > 5000:
            return 300  # 매우 큰 파일
        elif chunk_count > 2000:
            return 500  # 큰 파일
        elif chunk_count > 1000:
            return 800  # 중간 파일
        else:
            return 1000  # 작은 파일

    def _find_files_recursive(self) -> List[Path]:
        """처리할 파일들을 재귀적으로 찾습니다 (하위 디렉토리 포함)."""
        files = []

        # 지원하는 확장자
        supported_extensions = self.parser.supported_extensions

        # 재귀적으로 파일 검색
        for ext in supported_extensions:
            # 직접 파일 검색
            files.extend(self.input_dir.glob(f"*{ext}"))
            # 하위 디렉토리 파일 검색
            files.extend(self.input_dir.glob(f"**/*{ext}"))

        # 중복 제거 및 정렬
        files = list(set(files))
        files.sort()

        logger.info(f"파일 검색 완료: {len(files)}개 파일 발견")
        for file_path in files:
            logger.info(f"  - {file_path.relative_to(self.input_dir)}")

        return files

    def _print_summary(self, results: Dict[str, Any]):
        """결과 요약을 출력합니다."""
        logger.info("=" * 60)
        logger.info("벡터화 파이프라인 완료")
        logger.info("=" * 60)

        logger.info(f"총 파일 수: {results['total_files']}")
        logger.info(f"성공: {results['processed_files']}")
        logger.info(f"실패: {results['failed_files']}")
        logger.info(f"총 청크 수: {results['total_chunks']}")
        logger.info(f"실행 시간: {results['execution_time_seconds']:.2f}초")

        if results["failed_file_list"]:
            logger.warning("실패한 파일들:")
            for failed_file in results["failed_file_list"]:
                logger.warning(f"  - {failed_file}")

        # 벡터 저장소 통계
        stats = results.get("vector_store_stats", {})
        if stats:
            logger.info(f"벡터 저장소: {stats.get('collection_name', 'N/A')}")
            logger.info(f"저장된 문서 수: {stats.get('document_count', 0)}")
            logger.info(f"저장 위치: {stats.get('persist_directory', 'N/A')}")

    def retry_failed_files(
        self, failed_files: List[str], batch_delay: float = 0.5
    ) -> Dict[str, Any]:
        """실패한 파일들을 재처리합니다."""
        logger.info("=" * 60)
        logger.info("실패한 파일들 재처리 시작")
        logger.info("=" * 60)

        start_time = time.time()

        # 실패한 파일 경로들을 Path 객체로 변환
        failed_paths = [
            Path(file_path) for file_path in failed_files if Path(file_path).exists()
        ]

        if not failed_paths:
            logger.warning("재처리할 파일이 없습니다.")
            return {
                "status": "no_files",
                "message": "재처리할 파일이 없습니다.",
                "total_files": 0,
                "processed_files": 0,
                "failed_files": 0,
            }

        logger.info(f"재처리할 파일 수: {len(failed_paths)}")
        logger.info(f"배치 지연 시간: {batch_delay}초")

        # 파일별 처리
        results = {
            "total_files": len(failed_paths),
            "processed_files": 0,
            "failed_files": 0,
            "failed_file_list": [],
            "total_chunks": 0,
        }

        for file_path in failed_paths:
            try:
                logger.info(f"재처리 중: {file_path.name}")

                # 1. 파일 파싱
                parsed_data = self.parser.parse_file(file_path)
                if not parsed_data:
                    results["failed_files"] += 1
                    results["failed_file_list"].append(str(file_path))
                    continue

                # 2. 문서 청킹
                chunks = self.chunker.chunk_document(
                    parsed_data["content"], parsed_data["metadata"]
                )

                if not chunks:
                    logger.warning(f"청크가 생성되지 않았습니다: {file_path.name}")
                    results["failed_files"] += 1
                    results["failed_file_list"].append(str(file_path))
                    continue

                # 3. 벡터 저장 (배치 크기를 더 작게 설정)
                logger.info(
                    f"대용량 파일 처리: {file_path.name} ({len(chunks)}개 청크)"
                )
                batch_size = (
                    200 if batch_delay > 0.8 else 500
                )  # 극한 최적화 모드에서는 더 작은 배치

                if self.vector_store.add_documents(
                    chunks, batch_size=batch_size, batch_delay=batch_delay
                ):
                    results["processed_files"] += 1
                    results["total_chunks"] += len(chunks)
                    logger.info(f"재처리 완료: {file_path.name} ({len(chunks)}개 청크)")
                else:
                    results["failed_files"] += 1
                    results["failed_file_list"].append(str(file_path))

            except Exception as e:
                logger.error(f"파일 재처리 중 오류 ({file_path.name}): {e}")
                results["failed_files"] += 1
                results["failed_file_list"].append(str(file_path))

        # 실행 시간 계산
        end_time = time.time()
        execution_time = end_time - start_time

        results.update(
            {
                "execution_time_seconds": execution_time,
                "vector_store_stats": self.vector_store.get_collection_stats(),
            }
        )

        # 결과 요약
        self._print_retry_summary(results)

        return results

    def _print_retry_summary(self, results: Dict[str, Any]):
        """재처리 결과 요약을 출력합니다."""
        logger.info("=" * 60)
        logger.info("실패한 파일 재처리 완료")
        logger.info("=" * 60)

        logger.info(f"재처리 대상 파일 수: {results['total_files']}")
        logger.info(f"성공: {results['processed_files']}")
        logger.info(f"실패: {results['failed_files']}")
        logger.info(f"추가된 청크 수: {results['total_chunks']}")
        logger.info(f"실행 시간: {results['execution_time_seconds']:.2f}초")

        if results["failed_file_list"]:
            logger.warning("여전히 실패한 파일들:")
            for failed_file in results["failed_file_list"]:
                logger.warning(f"  - {failed_file}")

        # 벡터 저장소 통계
        stats = results.get("vector_store_stats", {})
        if stats:
            logger.info(f"벡터 저장소 총 문서 수: {stats.get('document_count', 0)}")


def main():
    """메인 실행 함수"""
    print("🚀 독립적인 문서 벡터화 스크립트")
    print("=" * 60)

    # 사용 안내
    print("\n📋 사용 방법:")
    print("1. 벡터화할 문서들을 data_source/raw/ 디렉토리 (하위 디렉토리 포함)에 저장")
    print("2. 지원 파일 형식: PDF, DOCX, XLSX, TXT")
    print("3. 스크립트 실행 후 결과 확인")
    print("\n📍 임베딩 모델 정보:")
    print("- config/llm.py의 get_embeddings() 함수 사용")
    print("- 모델: text-embedding-3-small (Azure OpenAI)")
    print("- 차원: 1536")
    print("- 벡터 저장소: data_source/vectorstore/")

    # 실행 모드 선택
    print("\n🔧 실행 모드 선택:")
    print("1. 전체 벡터화 (모든 파일 처리)")
    print("2. 실패한 파일만 재처리")

    while True:
        mode = input("\n모드를 선택하세요 (1/2): ").strip()
        if mode in ["1", "2"]:
            break
        print("올바른 모드를 선택해주세요 (1 또는 2).")

    if mode == "2":
        # 실패한 파일들 재처리
        failed_files = [
            "data_source/raw/1. 금융 규제 준수(Compliance)/[aws] cloudwatch.pdf",
            "data_source/raw/1. 금융 규제 준수(Compliance)/내부통제 및 거버넌스 참고사이트.txt",
            "data_source/raw/2. 내부통제 및 거버넌스/[aws] config.pdf",
            "data_source/raw/2. 내부통제 및 거버넌스/[기타] [국민권익위원회] 디지털시대 비용효율적인 청렴윤리경영.pdf",
            "data_source/raw/4. 개인정보·고객정보 보호/[aws] rds.pdf",
            "data_source/raw/8. 실시간 모니터링 및 자동화된 감사·보고/[aws] cloudwatch.pdf",
            "data_source/raw/8. 실시간 모니터링 및 자동화된 감사·보고/[aws] config.pdf",
            "data_source/raw/9. 레그테크(RegTech) 기반 자동화/[aws] config.pdf",
        ]

        print(f"\n📄 재처리할 파일 목록 ({len(failed_files)}개):")
        for i, file_path in enumerate(failed_files, 1):
            print(f"  {i}. {Path(file_path).name}")

        # 사용자 확인
        response = (
            input("\n실패한 파일들을 재처리하시겠습니까? (y/n): ").strip().lower()
        )
        if response != "y":
            print("작업이 취소되었습니다.")
            return

        # 재처리 실행
        try:
            pipeline = VectorizationPipeline()
            results = pipeline.retry_failed_files(failed_files)

            # 결과 파일 저장
            output_file = Path("retry_vectorization_results.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            print(f"\n📄 재처리 결과가 저장되었습니다: {output_file}")

            if results["processed_files"] > 0:
                print(
                    f"\n🎉 {results['processed_files']}개 파일이 성공적으로 재처리되었습니다!"
                )
                print(f"추가된 청크 수: {results['total_chunks']}")

            if results["failed_files"] > 0:
                print(f"\n⚠️ {results['failed_files']}개 파일이 여전히 실패했습니다.")
                print("더 작은 청크 크기로 재시도하거나 파일을 확인해주세요.")

        except Exception as e:
            logger.error(f"재처리 실행 중 오류 발생: {e}")
            print(f"\n❌ 재처리 실행 중 오류가 발생했습니다: {e}")

        return

    # 전체 벡터화 모드
    # 임베딩 호환성 미리 확인
    print("\n🔍 임베딩 호환성 사전 확인:")
    try:
        print("- config/llm.py의 get_embeddings() 함수 사용")
        print("- 모델: text-embedding-3-small (Azure OpenAI)")
        print("- 차원: 1536")
    except Exception as e:
        print(f"- 설정 확인 중 오류: {e}")

    # 환경 확인
    input_dir = Path("data_source/raw")
    if not input_dir.exists():
        print(f"\n❌ 입력 디렉토리가 없습니다: {input_dir}")
        print("디렉토리를 생성하고 문서 파일들을 넣어주세요.")
        return

    # 파일 확인 (하위 디렉토리 포함)
    supported_exts = {".pdf", ".docx", ".xlsx", ".xls", ".txt"}
    files = []
    for ext in supported_exts:
        files.extend(input_dir.glob(f"*{ext}"))
        files.extend(input_dir.glob(f"**/*{ext}"))

    files = list(set(files))  # 중복 제거

    if not files:
        print(f"\n❌ 처리할 파일이 없습니다: {input_dir}")
        print("PDF, DOCX, XLSX, TXT 파일을 넣어주세요.")
        return

    print(f"\n✅ {len(files)}개의 파일을 발견했습니다.")
    print("발견된 파일들:")
    for file_path in sorted(files):
        print(f"  - {file_path.relative_to(input_dir)}")

    # 사용자 확인
    response = input("\n계속 진행하시겠습니까? (y/n): ").strip().lower()
    if response != "y":
        print("작업이 취소되었습니다.")
        return

    # 벡터화 실행
    try:
        pipeline = VectorizationPipeline()
        results = pipeline.run()

        # 결과 파일 저장
        output_file = Path("vectorization_results.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n📄 결과가 저장되었습니다: {output_file}")

        if results["processed_files"] > 0:
            print("\n🎉 벡터화가 완료되었습니다!")
            print("이제 main.py를 실행하여 질의응답을 테스트할 수 있습니다.")
        else:
            print("\n⚠️ 벡터화된 파일이 없습니다. 오류를 확인해주세요.")

    except Exception as e:
        logger.error(f"벡터화 실행 중 오류 발생: {e}")
        print(f"\n❌ 벡터화 실행 중 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()
