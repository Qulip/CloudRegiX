from typing import Dict, Any, List, Generator
import time
import asyncio
import logging

from agents import (
    RouterAgent,
    PlannerAgent,
    AnswerAgent,
    ReActExecutorAgent,
    TraceManagerAgent,
)
from tools import (
    ReasoningTraceLogger,
    PlanRevisionTool,
    StateManager,
    SlideGeneratorTool,
)

# langchain-mcp-adapters를 사용한 MCP 도구 로딩
from langchain_mcp_adapters.client import MultiServerMCPClient

# 로거 설정
logger = logging.getLogger(__name__)


class CloudGovernanceOrchestrator:
    """
    클라우드 거버넌스 AI 시스템 하이브리드 오케스트레이터
    Plan & Execute + ReAct 하이브리드 방식으로 사용자 요청 처리
    """

    def __init__(self):
        self.router_agent = RouterAgent()
        self.planner_agent = PlannerAgent()
        self.answer_agent = AnswerAgent()

        # LangChain Tool 직접 사용
        self.slide_generator = SlideGeneratorTool()

        # 새로운 하이브리드 구성 요소들
        self.trace_manager = TraceManagerAgent()
        self.reasoning_trace_logger = ReasoningTraceLogger()
        self.plan_revision_tool = PlanRevisionTool()
        self.state_manager = StateManager()

        # ReAct Executor Pool
        self.executor_pool = {}
        self.max_executors = 5

        # MCP 도구들을 위한 MultiServerMCPClient 설정
        self.mcp_multi_client = None
        self.mcp_tools = []
        self._initialize_mcp_tools()

        self.mcp_context = {
            "role": "hybrid_orchestrator",
            "function": "hybrid_workflow_coordination",
            "agents_initialized": True,
            "hybrid_mode": True,
            "mcp_tools_available": True,
            "langchain_tools_available": True,
        }

    def _initialize_mcp_tools(self):
        """MCP 도구들을 초기화"""
        try:
            # MultiServerMCPClient 설정
            self.mcp_multi_client = MultiServerMCPClient(
                {
                    "cloud_governance": {
                        "url": "http://localhost:8001/tools",
                        "transport": "streamable_http",
                    }
                }
            )
            logger.info("✅ MCP MultiServerMCPClient 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ MCP 도구 초기화 실패: {str(e)}")
            self.mcp_multi_client = None

    async def _get_mcp_tools(self):
        """MCP 도구들을 비동기적으로 가져오기"""
        try:
            if self.mcp_multi_client:
                tools = await self.mcp_multi_client.get_tools()
                return tools
            return []
        except Exception as e:
            logger.warning(f"⚠️ MCP 도구 로딩 실패: {str(e)}")
            return []

    def _run_async_mcp_operation(self, coro):
        """비동기 MCP 작업을 동기적으로 실행"""
        try:
            loop = asyncio.get_running_loop()
            # 이미 실행 중인 루프가 있으면 새 스레드에서 실행
            import concurrent.futures
            import threading

            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()

        except RuntimeError:
            # 실행 중인 이벤트 루프가 없으면 새로 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    def process_request_streaming(
        self, user_input: str
    ) -> Generator[Dict[str, Any], None, None]:
        """
        스트리밍 방식으로 사용자 요청 처리하는 메서드

        Args:
            user_input (str): 사용자 입력

        Yields:
            Dict[str, Any]: 스트리밍 청크
        """
        start_time = time.time()

        try:
            logger.info(f"🚀 [ORCHESTRATOR] 스트리밍 처리 시작: {user_input[:50]}...")

            yield {
                "type": "progress",
                "stage": "router_analysis",
                "message": "사용자 의도를 분석하고 있습니다...",
                "progress": 0.1,
            }

            # 1단계: Router Agent - 의도 분석
            logger.info("📍 [STEP 1] Router Agent 실행 중...")
            router_result = self.router_agent({"user_input": user_input})
            intent = router_result.get("intent", "unknown")
            logger.info(f"✅ [ROUTER] 의도 분석 완료: {intent}")
            logger.info(f"📊 [ROUTER] 전체 결과: {router_result}")

            yield {
                "type": "progress",
                "stage": "planner_analysis",
                "message": f"실행 계획을 수립하고 있습니다... (의도: {intent})",
                "progress": 0.2,
                "intent": intent,
            }

            # 2단계: Enhanced Planner Agent - 하이브리드 실행 계획 수립
            logger.info("📋 [STEP 2] Planner Agent 실행 중...")
            planner_input = {**router_result, "user_input": user_input}
            logger.info(f"📥 [PLANNER] 입력 데이터: {planner_input}")
            plan_result = self.planner_agent(planner_input)
            logger.info("✅ [PLANNER] 계획 수립 완료")
            logger.info(f"📊 [PLANNER] 전체 결과: {plan_result}")

            execution_steps = plan_result.get("execution_steps", [])
            dependency_graph = plan_result.get("dependency_graph", {})

            logger.info(f"📋 [PLANNER] 실행 단계 수: {len(execution_steps)}")
            for i, step in enumerate(execution_steps):
                logger.info(
                    f"   Step {i+1}: {step.get('step_id', 'unknown')} - {step.get('description', 'No description')[:50]}..."
                )

            yield {
                "type": "progress",
                "stage": "execution_start",
                "message": f"{len(execution_steps)}개 단계의 실행을 시작합니다...",
                "progress": 0.3,
                "steps_count": len(execution_steps),
            }

            # 3단계: 하이브리드 실행 (스트리밍)
            logger.info(
                f"⚡ [STEP 3] 하이브리드 실행 시작 ({len(execution_steps)}개 단계)"
            )
            execution_context = {
                "user_input": user_input,
                "intent": intent,  # Router Agent에서 받은 intent 저장
                "key_entities": router_result.get("key_entities", []),
                "execution_steps": execution_steps,
                "execution_plan": execution_steps,
                "dependency_graph": dependency_graph,
                "execution_results": [],  # 단계별 결과를 누적할 리스트 추가
                "router_result": router_result,  # 전체 router 결과도 저장
            }

            # 단계별 실행을 스트리밍으로 처리
            execution_results = []
            for i, step in enumerate(execution_steps):
                step_progress = 0.3 + (0.5 * (i + 1) / len(execution_steps))
                step_id = step.get("step_id", f"step_{i+1}")
                step_description = step.get("description", "Unknown step")
                required_tools = step.get("required_tools", [])

                logger.info(f"\n   🔄 [STEP 3.{i+1}] 단계 실행 시작: {step_id}")
                logger.info(f"      📝 설명: {step_description}")
                logger.info(f"      🛠️  필요 도구: {required_tools}")

                yield {
                    "type": "progress",
                    "stage": "step_execution",
                    "message": f"단계 {i+1}/{len(execution_steps)} 실행 중: {step_description}",
                    "progress": step_progress,
                    "current_step": step_id,
                }

                try:
                    # 단계 실행 (스트리밍 지원)
                    logger.info(f"      🎯 [EXECUTION] 스트리밍 실행 시도...")
                    step_result = self._execute_step_streaming(step, execution_context)

                    if step_result:
                        logger.info(f"      ✅ [EXECUTION] 스트리밍 실행 성공")
                        final_result = None
                        chunk_count = 0

                        for chunk in step_result:
                            chunk_count += 1
                            logger.info(
                                f"         📦 [CHUNK {chunk_count}] 타입: {chunk.get('type', 'unknown')}"
                            )

                            # 도구 실행 과정을 스트리밍으로 전달
                            if chunk.get("type") in ["progress", "result", "error"]:
                                yield {
                                    "type": "tool_execution",
                                    "stage": chunk.get("stage", "unknown"),
                                    "message": chunk.get("message", ""),
                                    "progress": step_progress,
                                    "step_id": step_id,
                                    "chunk_data": chunk,
                                }

                                # 최종 결과가 나오면 저장
                        if chunk.get("type") == "result":
                            chunk_data = chunk.get("data", {})
                            # HTML이 포함된 데이터인 경우 잘리지 않도록 처리
                            if isinstance(chunk_data, dict) and "html" in str(
                                chunk_data
                            ):
                                final_result_data = chunk_data
                            else:
                                # 일반 데이터는 500자로 제한 (로그 가독성을 위해)
                                final_result_data = (
                                    str(chunk_data)[:500]
                                    if len(str(chunk_data)) > 500
                                    else chunk_data
                                )

                            final_result = {
                                "step_id": step_id,
                                "status": "success",
                                "result": chunk_data,
                                "final_result": final_result_data,
                                "tool": (
                                    required_tools[0] if required_tools else "unknown"
                                ),
                            }
                            logger.info(
                                f"         ✅ [RESULT] 최종 결과 저장: {final_result['status']}"
                            )

                        if final_result:
                            execution_results.append(final_result)
                            # 실행 컨텍스트에 결과 추가 (다음 단계에서 사용할 수 있도록)
                            if "execution_results" not in execution_context:
                                execution_context["execution_results"] = []
                            execution_context["execution_results"].append(final_result)
                            logger.info(
                                f"      ✅ [STEP 3.{i+1}] 완료 - 스트리밍 결과 저장됨"
                            )
                        else:
                            error_result = {
                                "step_id": step_id,
                                "status": "error",
                                "error": "스트리밍 실행 중 결과를 받지 못했습니다",
                                "tool": (
                                    required_tools[0] if required_tools else "unknown"
                                ),
                            }
                            execution_results.append(error_result)
                            if "execution_results" not in execution_context:
                                execution_context["execution_results"] = []
                            execution_context["execution_results"].append(error_result)
                            logger.info(
                                f"      ❌ [STEP 3.{i+1}] 실패 - 스트리밍 결과 없음"
                            )
                    else:
                        # 비스트리밍 실행
                        logger.info(f"      🔄 [EXECUTION] 비스트리밍 실행 시도...")
                        result = self._execute_single_step(step, execution_context)
                        execution_results.append(result)
                        # 실행 컨텍스트에 결과 추가
                        if "execution_results" not in execution_context:
                            execution_context["execution_results"] = []
                        execution_context["execution_results"].append(result)
                        logger.info(
                            f"      ✅ [STEP 3.{i+1}] 완료 - 비스트리밍 결과: {result.get('status', 'unknown')}"
                        )

                except Exception as e:
                    error_result = {
                        "step_id": step_id,
                        "status": "error",
                        "error": str(e),
                        "tool": required_tools[0] if required_tools else "unknown",
                    }
                    execution_results.append(error_result)
                    # 실행 컨텍스트에 결과 추가
                    if "execution_results" not in execution_context:
                        execution_context["execution_results"] = []
                    execution_context["execution_results"].append(error_result)
                    logger.info(f"      ❌ [STEP 3.{i+1}] 실행 실패: {str(e)}")

            logger.info(
                f"\n   ✅ [STEP 3] 하이브리드 실행 완료: {len(execution_results)}개 결과"
            )
            for i, result in enumerate(execution_results):
                logger.info(
                    f"      결과 {i+1}: {result.get('step_id', 'unknown')} - {result.get('status', 'unknown')}"
                )

            yield {
                "type": "progress",
                "stage": "trace_analysis",
                "message": "실행 결과를 분석하고 있습니다...",
                "progress": 0.8,
            }

            # 4단계: Trace Manager - 전체 추론 과정 분석
            logger.info(f"\n📊 [STEP 4] Trace Manager 실행 중...")
            trace_analysis = self._analyze_execution_trace(
                execution_results, execution_context
            )
            logger.info(
                f"   ✅ [TRACE] 분석 완료: {trace_analysis.get('final_assessment', {}).get('workflow_status', 'unknown')}"
            )

            yield {
                "type": "progress",
                "stage": "final_response",
                "message": "최종 응답을 생성하고 있습니다...",
                "progress": 0.9,
            }

            # 5단계: Answer Agent - 최종 응답 생성
            logger.info(f"\n✨ [STEP 5] Answer Agent 실행 중...")
            final_response = self._generate_final_response(
                execution_results, trace_analysis, execution_context
            )
            logger.info(f"   ✅ [ANSWER] 최종 응답 생성 완료")

            total_time = time.time() - start_time

            # 최종 결과
            final_data = {
                **final_response,
                "hybrid_execution_summary": {
                    "total_execution_time": f"{total_time:.2f}초",
                    "steps_executed": len(execution_results),
                    "successful_steps": len(
                        [r for r in execution_results if r.get("status") == "success"]
                    ),
                    "intent": intent,
                },
                "streaming": True,
            }

            logger.info(f"\n🎉 [ORCHESTRATOR] 스트리밍 처리 완료 ({total_time:.2f}초)")
            logger.info(
                f"   📊 성공한 단계: {final_data['hybrid_execution_summary']['successful_steps']}/{final_data['hybrid_execution_summary']['steps_executed']}"
            )

            yield {
                "type": "result",
                "stage": "completed",
                "message": "처리가 완료되었습니다.",
                "progress": 1.0,
                "data": final_data,
            }

        except Exception as e:
            logger.info(f"\n❌ [ORCHESTRATOR] 스트리밍 처리 중 오류: {str(e)}")
            import traceback

            traceback.print_exc()

            yield {
                "type": "error",
                "stage": "streaming_error",
                "message": f"스트리밍 처리 중 오류가 발생했습니다: {str(e)}",
                "error": str(e),
                "progress": 0.0,
            }

    def _execute_step_streaming(
        self, step: Dict[str, Any], context: Dict[str, Any]
    ) -> Generator:
        """
        개별 단계를 스트리밍으로 실행

        Args:
            step: 실행할 단계
            context: 실행 컨텍스트

        Returns:
            Generator 또는 None (스트리밍을 지원하지 않는 경우)
        """
        step_type = step.get("step_type", "general")
        required_tools = step.get("required_tools", [])
        step_id = step.get("step_id", "unknown")

        logger.info(
            f"         🎯 [STREAMING] 단계 타입: {step_type}, 도구: {required_tools}"
        )

        # MCP 도구 실행이 필요한 경우 (slide_draft 포함)
        if any(
            tool in required_tools
            for tool in ["rag_retriever", "report_summary", "slide_draft"]
        ):
            logger.info(f"         🔍 [STREAMING] MCP 도구 실행 필요 감지")
            yield from self._execute_mcp_tools_streaming(step, context)
            return

        # 슬라이드 생성 단계인 경우 (LangChain Tool)
        if (
            any(
                tool in required_tools
                for tool in ["slide_formatter", "format_slide", "slide_generator"]
            )
            or step_type == "generating"
        ):
            logger.info(f"         📊 [STREAMING] 슬라이드 생성 도구 감지")
            yield from self._execute_slide_generation_streaming(step, context)
            return

        # ReAct Executor가 필요한 복잡한 단계 (analysis, validation 등)
        if step_type in ["analysis", "validation"] and len(required_tools) > 1:
            logger.info(f"         🤖 [STREAMING] ReAct Executor 필요")
            yield from self._execute_react_streaming(step, context)
            return

        # drafting 단계 처리 (slide_draft 도구 사용)
        if step_type == "drafting":
            logger.info(f"         📝 [STREAMING] 초안 작성 단계 감지")
            yield from self._execute_mcp_tools_streaming(step, context)
            return

        # data_collection 단계 처리
        if step_type == "data_collection":
            logger.info(f"         📊 [STREAMING] 데이터 수집 단계 감지")
            yield from self._execute_mcp_tools_streaming(step, context)
            return

        # 기본적으로 스트리밍을 지원하지 않음
        logger.info(f"         ❌ [STREAMING] 스트리밍 미지원 단계: {step_type}")
        return None

    def _execute_mcp_tools_streaming(
        self, step: Dict[str, Any], context: Dict[str, Any]
    ) -> Generator:
        """MCP 도구를 스트리밍으로 실행"""
        step_id = step.get("step_id", "unknown")
        step_type = step.get("step_type", "general")
        required_tools = step.get("required_tools", [])

        logger.info(f"         🔧 [MCP] 비동기 MCP 도구 실행 시작...")

        yield {
            "type": "progress",
            "stage": "mcp_tool_execution",
            "message": "MCP 도구를 실행하고 있습니다...",
            "progress": 0.3,
        }

        try:
            # 단계별 실행
            result = self._execute_single_step(step, context)

            yield {
                "type": "result",
                "stage": "mcp_completed",
                "message": "MCP 도구 실행이 완료되었습니다.",
                "progress": 1.0,
                "data": result,
            }

        except Exception as e:
            logger.info(f"         ❌ [MCP] 실행 실패: {str(e)}")
            yield {
                "type": "error",
                "stage": "mcp_failed",
                "message": f"MCP 도구 실행 실패: {str(e)}",
                "progress": 0.0,
                "error": str(e),
            }

    def _execute_slide_generation_streaming(
        self, step: Dict[str, Any], context: Dict[str, Any]
    ) -> Generator:
        """슬라이드 생성을 스트리밍으로 실행"""
        step_id = step.get("step_id", "unknown")

        logger.info(f"         🎨 [SLIDE] 슬라이드 생성 시작...")

        yield {
            "type": "progress",
            "stage": "analyzing_draft",
            "message": "슬라이드 초안 분석 중...",
            "progress": 0.2,
        }

        yield {
            "type": "progress",
            "stage": "generating_structure",
            "message": "슬라이드 구조 생성 중...",
            "progress": 0.5,
        }

        yield {
            "type": "progress",
            "stage": "formatting_html",
            "message": "HTML 형식 변환 중...",
            "progress": 0.8,
        }

        try:
            # 실제 슬라이드 생성 실행
            result = self._execute_single_step(step, context)

            yield {
                "type": "result",
                "stage": "completed",
                "message": "슬라이드 생성 완료",
                "progress": 1.0,
                "data": result,
            }

        except Exception as e:
            logger.info(f"         ❌ [SLIDE] 생성 실패: {str(e)}")
            yield {
                "type": "error",
                "stage": "slide_failed",
                "message": f"슬라이드 생성 실패: {str(e)}",
                "progress": 0.0,
                "error": str(e),
            }

    def _execute_react_streaming(
        self, step: Dict[str, Any], context: Dict[str, Any]
    ) -> Generator:
        """ReAct Executor를 스트리밍으로 실행"""
        step_id = step.get("step_id", "unknown")

        logger.info(f"         🤖 [REACT] ReAct Executor 실행 시작...")

        yield {
            "type": "progress",
            "stage": "react_thinking",
            "message": "추론 과정을 실행하고 있습니다...",
            "progress": 0.3,
        }

        try:
            # ReAct Executor 실행
            result = self._execute_single_step(step, context)

            yield {
                "type": "result",
                "stage": "react_completed",
                "message": "ReAct 실행이 완료되었습니다.",
                "progress": 1.0,
                "data": result,
            }

        except Exception as e:
            logger.info(f"         ❌ [REACT] 실행 실패: {str(e)}")
            yield {
                "type": "error",
                "stage": "react_failed",
                "message": f"ReAct 실행 실패: {str(e)}",
                "progress": 0.0,
                "error": str(e),
            }

    def _execute_single_step(
        self, step: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        개별 단계 실행 (MCP 도구 직접 실행 또는 ReAct 실행기 사용)

        Args:
            step: 실행할 단계
            context: 실행 컨텍스트

        Returns:
            실행 결과
        """
        step_id = step.get("step_id", "unknown")
        step_type = step.get("step_type", "general")
        required_tools = step.get("required_tools", [])
        step_description = step.get("description", "")

        logger.info(f"      🔄 [SINGLE_STEP] 단계 실행 시작: {step_id}")
        logger.info(f"         📝 설명: {step_description}")
        logger.info(f"         🛠️  도구: {required_tools}")
        logger.info(f"         📊 타입: {step_type}")

        try:
            # 도구 이름 정규화
            logger.info(f"         🔧 [NORMALIZE] 도구 이름 정규화 시작...")
            normalized_tools = []
            for tool in required_tools:
                if tool in [
                    "rag_retriever",
                    "search_documents",
                    "data_analyzer",
                    "content_validator",
                ]:
                    normalized_tools.append("search_documents")
                    logger.info(f"            ✅ '{tool}' → 'search_documents'")
                elif tool in ["slide_formatter", "format_slide", "slide_generator"]:
                    # 슬라이드 생성은 LangChain Tool로 직접 처리
                    normalized_tools.append("slide_generator_langchain")
                    logger.info(
                        f"            ✅ '{tool}' → 'slide_generator_langchain'"
                    )
                elif tool in ["slide_draft", "create_slide_draft"]:
                    # 슬라이드 초안 생성은 MCP 도구로 처리
                    normalized_tools.append("create_slide_draft")
                    logger.info(f"            ✅ '{tool}' → 'create_slide_draft'")
                elif tool in [
                    "report_summary",
                    "summarize_report",
                    "content_generator",
                ]:
                    normalized_tools.append("summarize_report")
                    logger.info(f"            ✅ '{tool}' → 'summarize_report'")
                elif tool in ["get_tool_status"]:
                    normalized_tools.append("get_tool_status")
                    logger.info(f"            ✅ '{tool}' → 'get_tool_status'")
                else:
                    normalized_tools.append("search_documents")
                    logger.info(f"            ⚠️ '{tool}' → 'search_documents' (기본값)")

            logger.info(f"         📋 [NORMALIZE] 정규화된 도구: {normalized_tools}")

            # LangChain Tool 직접 실행 (슬라이드 생성)
            if "slide_generator_langchain" in normalized_tools:
                logger.info(f"         🎨 [LANGCHAIN] SlideGenerator 도구 직접 실행")

                # 사용자 입력에서 콘텐츠 추출
                user_input = context.get("user_input", "")

                # 이전 단계에서 검색 결과와 슬라이드 초안 가져오기
                search_results = []
                # 기본 슬라이드 초안 (폴백용) - 실제 데이터가 없을 때만 사용
                slide_draft = None

                # 실행 결과에서 이전 단계 결과들 수집
                execution_results = context.get("execution_results", [])
                logger.info(
                    f"            📋 [LANGCHAIN] 이전 단계 결과 수: {len(execution_results)}"
                )

                # 디버깅: 모든 결과의 tool 이름 출력
                for i, prev_result in enumerate(execution_results):
                    tool_name = prev_result.get("tool", "unknown")
                    original_tools = prev_result.get("original_tools", [])
                    status = prev_result.get("status", "unknown")
                    logger.info(
                        f"            🔍 [DEBUG] 결과 {i+1}: tool='{tool_name}', original_tools={original_tools}, status='{status}'"
                    )

                for prev_result in execution_results:
                    result_tool = prev_result.get("tool", "")
                    original_tools = prev_result.get("original_tools", [])
                    result_data = prev_result.get("result", {})

                    # 검색 결과 추출
                    if result_tool == "search_documents":
                        try:
                            if isinstance(result_data, str):
                                import json

                                result_data = json.loads(result_data)
                            search_results = result_data.get("results", [])
                            logger.info(
                                f"            ✅ [LANGCHAIN] 검색 결과 획득: {len(search_results)}개"
                            )
                        except Exception as e:
                            logger.info(
                                f"            ⚠️ [LANGCHAIN] 검색 결과 파싱 실패: {e}"
                            )

                    # 슬라이드 초안 추출 - 원본 도구와 현재 도구 모두 확인
                    elif result_tool in ["create_slide_draft", "slide_draft"] or any(
                        tool in original_tools
                        for tool in ["slide_draft", "create_slide_draft"]
                    ):
                        logger.info(
                            f"            🔍 [DEBUG] 슬라이드 초안 후보 발견: tool='{result_tool}'"
                        )
                        try:
                            # 결과 데이터에서 draft 찾기
                            draft_found = False

                            logger.info(
                                f"            🔍 [DEBUG] 원본 데이터 타입: {type(result_data)}"
                            )
                            logger.info(
                                f"            🔍 [DEBUG] 원본 데이터 미리보기: {str(result_data)[:300]}..."
                            )

                            # MCP 도구 결과 파싱 로직
                            parsed_result_data = None
                            import json

                            # Case 1: result_data가 dict이고 'result' 키에 JSON 문자열이 있는 경우
                            if (
                                isinstance(result_data, dict)
                                and "result" in result_data
                            ):
                                result_content = result_data["result"]
                                logger.info(
                                    f"            🔍 [DEBUG] result_data는 dict, result 키 확인: {type(result_content)}"
                                )

                                if isinstance(result_content, str):
                                    try:
                                        parsed_result_data = json.loads(result_content)
                                        logger.info(
                                            f"            📋 [DEBUG] result 키의 JSON 문자열 파싱 성공"
                                        )
                                    except json.JSONDecodeError as e:
                                        logger.info(
                                            f"            ⚠️ [DEBUG] result 키 JSON 파싱 실패: {e}"
                                        )
                                        # 이스케이프된 JSON 처리 시도
                                        if (
                                            '"draft"' in result_content
                                            and '"markdown_content"' in result_content
                                        ):
                                            try:
                                                cleaned_data = result_content.replace(
                                                    '\\"', '"'
                                                ).replace("\\n", "\n")
                                                parsed_result_data = json.loads(
                                                    cleaned_data
                                                )
                                                logger.info(
                                                    f"            📋 [DEBUG] result 키 클린업 후 JSON 파싱 성공"
                                                )
                                            except Exception as cleanup_e:
                                                logger.info(
                                                    f"            ⚠️ [DEBUG] result 키 클린업 후에도 파싱 실패: {cleanup_e}"
                                                )
                                elif isinstance(result_content, dict):
                                    parsed_result_data = result_content
                                    logger.info(
                                        f"            📋 [DEBUG] result 키가 이미 dict 형태"
                                    )

                            # Case 2: result_data 자체가 JSON 문자열인 경우
                            elif isinstance(result_data, str):
                                try:
                                    parsed_result_data = json.loads(result_data)
                                    logger.info(
                                        f"            📋 [DEBUG] result_data 전체 JSON 파싱 성공"
                                    )
                                except json.JSONDecodeError as e:
                                    logger.info(
                                        f"            ⚠️ [DEBUG] result_data 전체 JSON 파싱 실패: {e}"
                                    )
                                    if (
                                        '"draft"' in result_data
                                        and '"markdown_content"' in result_data
                                    ):
                                        try:
                                            cleaned_data = result_data.replace(
                                                '\\"', '"'
                                            ).replace("\\n", "\n")
                                            parsed_result_data = json.loads(
                                                cleaned_data
                                            )
                                            logger.info(
                                                f"            📋 [DEBUG] result_data 클린업 후 JSON 파싱 성공"
                                            )
                                        except Exception as cleanup_e:
                                            logger.info(
                                                f"            ⚠️ [DEBUG] result_data 클린업 후에도 파싱 실패: {cleanup_e}"
                                            )

                            # Case 3: result_data가 이미 dict인 경우 (draft가 직접 포함된 경우)
                            elif isinstance(result_data, dict):
                                # 먼저 직접 draft 확인
                                if result_data.get("draft"):
                                    parsed_result_data = result_data
                                    logger.info(
                                        f"            📋 [DEBUG] result_data에 직접 draft 포함됨"
                                    )
                                else:
                                    logger.info(
                                        f"            ⚠️ [DEBUG] result_data가 dict이지만 draft 또는 result 키가 없음"
                                    )

                            if parsed_result_data is None:
                                logger.info(
                                    f"            ⚠️ [DEBUG] 모든 파싱 시도 실패"
                                )
                                continue

                            # 파싱된 데이터에서 슬라이드 초안 찾기
                            if isinstance(parsed_result_data, dict):
                                logger.info(
                                    f"            🔍 [DEBUG] dict 객체에서 키 검색: {list(parsed_result_data.keys())}"
                                )

                                # 직접 draft 키 확인
                                if parsed_result_data.get("draft"):
                                    draft_candidate = parsed_result_data.get("draft")
                                    if isinstance(
                                        draft_candidate, dict
                                    ) and draft_candidate.get("markdown_content"):
                                        slide_draft = draft_candidate
                                        draft_found = True
                                        logger.info(
                                            f"            ✅ [DEBUG] draft 키에서 초안 발견"
                                        )

                                # slide_draft 키 확인
                                elif parsed_result_data.get("slide_draft"):
                                    draft_candidate = parsed_result_data.get(
                                        "slide_draft"
                                    )
                                    if isinstance(
                                        draft_candidate, dict
                                    ) and draft_candidate.get("markdown_content"):
                                        slide_draft = draft_candidate
                                        draft_found = True
                                        logger.info(
                                            f"            ✅ [DEBUG] slide_draft 키에서 초안 발견"
                                        )

                                # 모든 키를 순회하며 draft 관련 데이터 찾기
                                if not draft_found:
                                    for key, value in parsed_result_data.items():
                                        logger.info(
                                            f"            🔍 [DEBUG] 키 '{key}' 검사 중..."
                                        )
                                        if "draft" in key.lower() and isinstance(
                                            value, dict
                                        ):
                                            if value.get("markdown_content"):
                                                slide_draft = value
                                                draft_found = True
                                                logger.info(
                                                    f"            ✅ [DEBUG] '{key}' 키에서 초안 발견"
                                                )
                                                break
                                        elif isinstance(value, dict):
                                            # 중첩된 객체에서도 찾기
                                            for (
                                                nested_key,
                                                nested_value,
                                            ) in value.items():
                                                if (
                                                    "draft" in nested_key.lower()
                                                    and isinstance(nested_value, dict)
                                                ):
                                                    if nested_value.get(
                                                        "markdown_content"
                                                    ):
                                                        slide_draft = nested_value
                                                        draft_found = True
                                                        logger.info(
                                                            f"            ✅ [DEBUG] 중첩 키 '{key}.{nested_key}'에서 초안 발견"
                                                        )
                                                        break
                                            if draft_found:
                                                break

                            if draft_found and slide_draft:
                                content_preview = slide_draft.get(
                                    "markdown_content", ""
                                )[:100]
                                logger.info(
                                    f"            ✅ [LANGCHAIN] 슬라이드 초안 획득: 마크다운 형식 ({slide_draft.get('format', 'unknown')})"
                                )
                                logger.info(
                                    f"            📝 [LANGCHAIN] 초안 내용 미리보기: {content_preview}..."
                                )
                                logger.info(
                                    f"            📏 [LANGCHAIN] 초안 전체 길이: {len(slide_draft.get('markdown_content', ''))}자"
                                )
                                # 초안을 찾았으므로 루프 종료
                                break
                            else:
                                logger.info(
                                    f"            ⚠️ [DEBUG] 초안 데이터를 찾을 수 없음"
                                )

                        except Exception as e:
                            logger.info(
                                f"            ⚠️ [LANGCHAIN] 슬라이드 초안 파싱 실패: {e}"
                            )
                            import traceback

                            logger.info(
                                f"            🔍 [DEBUG] 상세 오류: {traceback.format_exc()}"
                            )

                # 슬라이드 초안이 없을 경우에만 기본 폴백 생성
                if slide_draft is None:
                    slide_draft = {
                        "markdown_content": f"""# 슬라이드 1

주제: {user_input}의 개요

요약 내용: {user_input}에 대한 개요와 배경을 설명합니다.

# 슬라이드 2

주제: 주요 구성 요소

요약 내용: {user_input}의 주요 구성 요소를 다룹니다.

# 슬라이드 3

주제: 결론 및 제언

요약 내용: {user_input}에 대한 결론과 향후 제언사항을 제시합니다.""",
                        "format": "markdown_fallback",
                    }
                    logger.info(
                        f"            ⚠️ [LANGCHAIN] 슬라이드 초안 없음 - 폴백 데이터 사용"
                    )
                else:
                    logger.info(
                        f"            ✅ [LANGCHAIN] 슬라이드 초안 발견 - 실제 데이터 사용"
                    )

                slide_inputs = {
                    "slide_draft": slide_draft,
                    "search_results": search_results,
                    "user_input": user_input,
                }

                logger.info(f"            📋 [LANGCHAIN] 최종 슬라이드 입력:")
                logger.info(
                    f"                - 초안 형식: {slide_draft.get('format', 'unknown')}"
                )
                logger.info(f"                - 검색 결과: {len(search_results)}개")
                logger.info(f"                - 사용자 입력: {user_input[:50]}...")
                logger.info(f"            ▶️  [LANGCHAIN] SlideGenerator 실행 중...")

                result = self.slide_generator.run(slide_inputs)

                logger.info(f"            ✅ [LANGCHAIN] SlideGenerator 실행 완료")
                logger.info(f"            📊 [LANGCHAIN] 결과 타입: {type(result)}")

                return {
                    "step_id": step_id,
                    "step_type": step_type,
                    "tool": "slide_generator_langchain",
                    "status": "success",
                    "result": result,
                    "final_result": result.get("html", ""),  # HTML 전체를 유지
                }

            # MCP 도구 실행 (단일 도구)
            elif len(normalized_tools) == 1 and normalized_tools[0] in [
                "search_documents",
                "summarize_report",
                "create_slide_draft",
                "get_tool_status",
            ]:
                tool_name = normalized_tools[0]
                logger.info(f"         🔧 [MCP] MCP 도구 실행: {tool_name}")

                # MCP 도구 실행을 위한 비동기 함수
                async def execute_mcp_tool():
                    try:
                        logger.info(f"            🔗 [MCP] MCP 클라이언트 확인...")
                        if not self.mcp_multi_client:
                            raise Exception("MCP 클라이언트가 초기화되지 않았습니다")

                        logger.info(
                            f"            📋 [MCP] MCP 도구 목록 가져오는 중..."
                        )
                        # MCP 도구들 가져오기
                        tools = await self._get_mcp_tools()
                        logger.info(
                            f"            📊 [MCP] 사용 가능한 도구 수: {len(tools)}"
                        )

                        if tools:
                            tool_names = [tool.name for tool in tools]
                            logger.info(f"            📋 [MCP] 도구 목록: {tool_names}")

                        # 해당 도구 찾기
                        target_tool = None
                        for tool in tools:
                            if tool.name == tool_name:
                                target_tool = tool
                                break

                        if not target_tool:
                            available_tools = (
                                [tool.name for tool in tools] if tools else []
                            )
                            raise Exception(
                                f"MCP 도구 '{tool_name}'을 찾을 수 없습니다. 사용 가능한 도구: {available_tools}"
                            )

                        logger.info(
                            f"            ✅ [MCP] 대상 도구 발견: {target_tool.name}"
                        )

                        # 도구별 매개변수 설정
                        if tool_name == "search_documents":
                            params = step.get("parameters", {})
                            if not params:
                                description = step.get("description", "")
                                user_input = context.get("user_input", "")

                                # 검색 쿼리 결정
                                if (
                                    "클라우드 거버넌스" in description
                                    or "클라우드 거버넌스" in user_input
                                ):
                                    query = "클라우드 거버넌스"
                                elif "보안" in description or "보안" in user_input:
                                    query = "클라우드 보안"
                                elif "정책" in description or "정책" in user_input:
                                    query = "클라우드 정책"
                                else:
                                    query = user_input[:50] or "클라우드 거버넌스"

                                params = {"query": query, "top_k": 7}

                            logger.info(
                                f"            📋 [MCP] search_documents 매개변수: {params}"
                            )
                            logger.info(
                                f"            ▶️  [MCP] search_documents 실행 중..."
                            )
                            result = await target_tool.ainvoke(params)
                            logger.info(
                                f"            ✅ [MCP] search_documents 실행 완료"
                            )

                        elif tool_name == "create_slide_draft":
                            # 이전 단계에서 검색 결과 가져오기
                            search_results = []
                            for prev_result in context.get("execution_results", []):
                                if prev_result.get("tool") == "search_documents":
                                    try:
                                        result_data = prev_result.get("result", {})
                                        if isinstance(result_data, str):
                                            import json

                                            result_data = json.loads(result_data)
                                        search_results = result_data.get("results", [])
                                        break
                                    except:
                                        pass

                            params = {
                                "search_results": search_results,
                                "user_input": context.get("user_input", ""),
                            }

                            logger.info(
                                f"            📋 [MCP] create_slide_draft 매개변수: {len(search_results)}개 검색 결과"
                            )
                            logger.info(
                                f"            ▶️  [MCP] create_slide_draft 실행 중..."
                            )
                            result = await target_tool.ainvoke(params)
                            logger.info(
                                f"            ✅ [MCP] create_slide_draft 실행 완료"
                            )

                        elif tool_name == "summarize_report":
                            params = step.get("parameters", {})
                            if not params:
                                params = {
                                    "content": context.get(
                                        "user_input", "클라우드 거버넌스 보고서"
                                    ),
                                    "title": "클라우드 전환 제안서",
                                }

                            logger.info(
                                f"            📋 [MCP] summarize_report 매개변수: {params}"
                            )
                            logger.info(
                                f"            ▶️  [MCP] summarize_report 실행 중..."
                            )
                            result = await target_tool.ainvoke(params)
                            logger.info(
                                f"            ✅ [MCP] summarize_report 실행 완료"
                            )

                        elif tool_name == "get_tool_status":
                            logger.info(
                                f"            ▶️  [MCP] get_tool_status 실행 중..."
                            )
                            result = await target_tool.ainvoke({})
                            logger.info(
                                f"            ✅ [MCP] get_tool_status 실행 완료"
                            )

                        logger.info(f"            📊 [MCP] 결과 타입: {type(result)}")
                        logger.info(
                            f"            📋 [MCP] 결과 미리보기: {str(result)[:200]}..."
                        )

                        # HTML이 포함된 경우 잘리지 않도록 처리
                        if isinstance(result, dict) and "html" in str(result):
                            final_result_data = result
                        else:
                            # 일반 데이터는 500자로 제한 (로그 가독성을 위해)
                            final_result_data = (
                                str(result)[:500] if len(str(result)) > 500 else result
                            )

                        return {
                            "step_id": step_id,
                            "step_type": step_type,
                            "tool": tool_name,
                            "original_tools": required_tools,  # 원래 도구 이름들 보존
                            "status": "success",
                            "result": result,
                            "final_result": final_result_data,
                        }

                    except Exception as e:
                        logger.info(f"            ❌ [MCP] 도구 실행 실패: {str(e)}")
                        import traceback

                        traceback.print_exc()
                        return {
                            "step_id": step_id,
                            "step_type": step_type,
                            "tool": tool_name,
                            "status": "error",
                            "error": str(e),
                        }

                # 비동기 MCP 도구 실행
                logger.info(f"            🔄 [MCP] 비동기 실행 시작...")
                result = self._run_async_mcp_operation(execute_mcp_tool())
                logger.info(
                    f"            ✅ [MCP] 비동기 실행 완료: {result.get('status', 'unknown')}"
                )
                return result

            else:
                # ReAct 실행기를 통한 실행 (복합 도구 또는 추론이 필요한 경우)
                logger.info(
                    f"         🤖 [REACT] ReAct Executor로 전달: {normalized_tools}"
                )
                executor = self._get_or_create_executor(step_id)
                logger.info(f"            📋 [REACT] Executor ID: {step_id}")
                logger.info(f"            ▶️  [REACT] 실행 중...")
                result = executor.execute_step(step, context)
                logger.info(
                    f"            ✅ [REACT] 실행 완료: {result.get('status', 'unknown')}"
                )
                return result

        except Exception as e:
            logger.info(f"         ❌ [SINGLE_STEP] 단계 실행 실패: {str(e)}")
            import traceback

            traceback.print_exc()
            return {
                "step_id": step_id,
                "step_type": step_type,
                "tool": required_tools[0] if required_tools else "unknown",
                "status": "error",
                "error": str(e),
            }

    def _generate_direct_answer(self, user_input: str) -> str:
        """
        일반적인 대화를 위한 직접 응답 생성

        Args:
            user_input (str): 사용자 입력

        Returns:
            str: 직접 응답
        """
        # 간단한 인사나 일반 대화 처리
        user_input_lower = user_input.lower()

        if any(
            greeting in user_input_lower
            for greeting in ["안녕", "하이", "헬로", "시작"]
        ):
            return """
안녕하세요! 👋 

저는 클라우드 거버넌스 전문 AI 어시스턴트입니다.

**제가 도와드릴 수 있는 것들:**
• 클라우드 거버넌스 관련 질문 답변
• 정책 및 컴플라이언스 가이드
• 슬라이드 및 프레젠테이션 자료 생성
• 모니터링 및 관리 방안 제시

무엇을 도와드릴까요?
"""

        elif any(
            help_word in user_input_lower
            for help_word in ["도움", "help", "뭐 할 수", "기능"]
        ):
            return """
**클라우드 거버넌스 AI 어시스턴트 기능 안내** 📚

🔍 **질문 응답**
- 클라우드 거버넌스 정책
- 컴플라이언스 요구사항
- 보안 관리 방안
- 모니터링 전략

📊 **슬라이드 생성**
- 프레젠테이션 자료 작성
- 개념 정리 슬라이드
- 비교 분석 자료

예시: "클라우드 보안 정책에 대해 알려주세요" 또는 "데이터 거버넌스 슬라이드 만들어주세요"
"""

        else:
            return """
클라우드 거버넌스와 관련된 구체적인 질문이나 요청을 해주시면 더 도움이 될 것 같습니다.

예를 들어:
• "클라우드 보안 정책이 무엇인가요?"
• "컴플라이언스 관리 방안 슬라이드 만들어주세요"
• "데이터 거버넌스 모범 사례를 알려주세요"

어떤 도움이 필요하신지 말씀해 주세요! 😊
"""

    def _get_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime

        return datetime.now().isoformat()

    def _get_or_create_executor(self, executor_id: str) -> ReActExecutorAgent:
        """ReAct Executor 생성 또는 기존 것 반환"""
        if executor_id not in self.executor_pool:
            if len(self.executor_pool) >= self.max_executors:
                # 풀이 가득 찬 경우 가장 오래된 것 제거
                oldest_key = next(iter(self.executor_pool))
                del self.executor_pool[oldest_key]

            self.executor_pool[executor_id] = ReActExecutorAgent(executor_id)

        return self.executor_pool[executor_id]

    def _analyze_execution_trace(
        self, execution_results: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """전체 실행 추적 분석"""
        trace_input = {
            "execution_results": execution_results,
            "failed_steps": [
                r
                for r in execution_results
                if r.get("status") not in ["success", "partial_success"]
            ],
            "context": context,
        }

        return self.trace_manager(trace_input)

    def _handle_failure_recovery(
        self,
        execution_results: List[Dict[str, Any]],
        context: Dict[str, Any],
        trace_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """실패 복구 처리"""
        failed_steps = [
            r
            for r in execution_results
            if r.get("status") not in ["success", "partial_success"]
        ]

        if not failed_steps:
            return {"recovery_status": "no_recovery_needed"}

        # 기본 복구: 단순히 재시도 권장
        return {
            "recovery_status": "completed",
            "recovery_strategy": "retry_recommended",
            "recovered_results": execution_results,
        }

    def _generate_final_response(
        self,
        execution_results: List[Dict[str, Any]],
        trace_analysis: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """최종 응답 생성"""
        # 성공한 결과들에서 최종 답변 추출
        successful_results = [
            r for r in execution_results if r.get("status") == "success"
        ]

        if successful_results:
            latest_result = successful_results[-1]
            answer_content = latest_result.get("final_result", "")
        else:
            # 부분 성공이라도 사용
            partial_results = [
                r for r in execution_results if r.get("status") == "partial_success"
            ]
            if partial_results:
                answer_content = partial_results[-1].get("final_result", "")
            else:
                answer_content = "요청을 처리하는 중 문제가 발생했습니다."

        # 슬라이드 생성 관련 데이터 추출
        slide_data = {}
        slide_html = ""
        for result in execution_results:
            if result.get("tool") in ["slide_generator_langchain", "slide_generator"]:
                result_data = result.get("result", {})
                if isinstance(result_data, dict):
                    slide_data = result_data
                    slide_html = result_data.get("html", "")
                    break

        # Answer Agent 입력 구성
        answer_input = {
            "agent_type": "hybrid_execution",
            "intent": context.get("intent"),  # Router Agent에서 받은 intent 전달
            "answer_content": answer_content,
            "execution_results": execution_results,
            "reasoning_trace": self.reasoning_trace_logger.get_global_trace(),
            "trace_summary": trace_analysis.get("trace_summary", {}),
            "overall_confidence": trace_analysis.get("final_assessment", {}).get(
                "confidence", 0.5
            ),
            "source_type": "hybrid_react",
            "context": context,  # 전체 컨텍스트 전달
            "user_input": context.get("user_input", ""),  # 명시적으로 user_input 전달
            # 슬라이드 생성 관련 데이터
            "slide_data": slide_data,
            "slide_html": slide_html,
        }

        return self.answer_agent(answer_input)

    def _create_error_response(
        self, error_message: str, execution_time: float
    ) -> Dict[str, Any]:
        """오류 응답 생성"""
        return {
            "final_answer": f"시스템 처리 중 오류가 발생했습니다: {error_message}\n\n하이브리드 AI 시스템이 복구를 시도했지만 완전한 처리가 어려웠습니다. 다시 시도해 주세요.",
            "timestamp": self._get_timestamp(),
            "hybrid_execution_summary": {
                "total_execution_time": f"{execution_time:.2f}초",
                "steps_executed": 0,
                "successful_steps": 0,
                "reasoning_depth": "error",
                "overall_confidence": 0.0,
            },
            "mcp_context": {
                **self.mcp_context,
                "status": "error",
                "error_message": error_message,
                "hybrid_mode_used": False,
                "total_time": execution_time,
            },
        }

    def get_system_status(self) -> Dict[str, Any]:
        """
        하이브리드 시스템 상태 확인

        Returns:
            Dict[str, Any]: 시스템 상태 정보
        """
        # MCP 도구 상태 확인
        mcp_tools_status = "unavailable"
        try:
            if self.mcp_multi_client:
                # 비동기 도구 상태 확인
                async def check_mcp_status():
                    try:
                        tools = await self._get_mcp_tools()
                        return "available" if len(tools) > 0 else "empty"
                    except:
                        return "error"

                mcp_tools_status = self._run_async_mcp_operation(check_mcp_status())
            else:
                mcp_tools_status = "not_initialized"
        except Exception as e:
            mcp_tools_status = f"error: {str(e)}"

        return {
            "orchestrator": "hybrid_running",
            "agents": {
                "router": "initialized",
                "enhanced_planner": "initialized",
                "answer": "enhanced",
                "trace_manager": "initialized",
            },
            "react_executors": {
                "pool_size": len(self.executor_pool),
                "max_executors": self.max_executors,
                "active_executors": list(self.executor_pool.keys()),
            },
            "tools": {
                "reasoning_trace_logger": "active",
                "plan_revision_tool": "active",
                "state_manager": "active",
                "slide_generator_langchain": "available",
                "mcp_tools": mcp_tools_status,
            },
            "mcp_integration": {
                "multi_client_initialized": self.mcp_multi_client is not None,
                "tools_status": mcp_tools_status,
            },
            "hybrid_features": {
                "parallel_execution": False,  # 향후 구현
                "react_reasoning": True,
                "failure_recovery": True,
                "trace_analysis": True,
                "streaming_support": True,
            },
            "mcp_context": self.mcp_context,
        }

    def clear_execution_state(self):
        """실행 상태 초기화"""
        self.executor_pool.clear()
        self.reasoning_trace_logger.clear_traces()
        self.plan_revision_tool.clear_history()
        self.state_manager.clear_all_states()
        logger.info("🧹 하이브리드 실행 상태 초기화 완료")
