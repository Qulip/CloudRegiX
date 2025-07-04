from typing import Dict, Any, List, Generator
import time
import asyncio

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
    SlideFormatterTool,
)
from mcp_client import get_mcp_client

# langchain-mcp-adapters를 사용한 MCP 도구 로딩
from langchain_mcp_adapters.client import MultiServerMCPClient


class CloudGovernanceOrchestrator:
    """
    클라우드 거버넌스 AI 시스템 하이브리드 오케스트레이터
    Plan & Execute + ReAct 하이브리드 방식으로 사용자 요청 처리
    """

    def __init__(self):
        self.router_agent = RouterAgent()
        self.planner_agent = PlannerAgent()
        self.answer_agent = AnswerAgent()

        # 기존 MCP 클라이언트 (호환성 유지)
        self.mcp_client = get_mcp_client()

        # LangChain Tool 직접 사용
        self.slide_formatter = SlideFormatterTool()

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
            print("✅ MCP MultiServerMCPClient 초기화 완료")
        except Exception as e:
            print(f"⚠️ MCP 도구 초기화 실패: {str(e)}")
            self.mcp_multi_client = None

    async def _get_mcp_tools(self):
        """MCP 도구들을 비동기적으로 가져오기"""
        try:
            if self.mcp_multi_client:
                tools = await self.mcp_multi_client.get_tools()
                return tools
            return []
        except Exception as e:
            print(f"⚠️ MCP 도구 로딩 실패: {str(e)}")
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

    def process_request(self, user_input: str) -> Dict[str, Any]:
        """
        하이브리드 방식으로 사용자 요청 처리하는 메인 메서드

        Args:
            user_input (str): 사용자 입력

        Returns:
            Dict[str, Any]: 최종 응답
        """
        start_time = time.time()

        try:
            print(f"🚀 하이브리드 처리 시작: {user_input[:50]}...")

            # 1단계: Router Agent - 의도 분석
            print("\n📍 1단계: Router Agent - 의도 분석")
            router_result = self.router_agent({"user_input": user_input})
            print(f"   └ Intent: {router_result.get('intent', 'unknown')}")

            # 2단계: Enhanced Planner Agent - 하이브리드 실행 계획 수립
            print("\n📋 2단계: Enhanced Planner - 하이브리드 실행 계획 수립")
            planner_input = {**router_result, "user_input": user_input}
            plan_result = self.planner_agent(planner_input)

            return self._process_hybrid_execution(
                plan_result, router_result, user_input, start_time
            )

        except Exception as e:
            error_time = time.time() - start_time
            print(f"\n❌ 하이브리드 오케스트레이터 오류: {str(e)}")
            return self._create_error_response(str(e), error_time)

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
            print(f"\n🚀 [ORCHESTRATOR] 스트리밍 처리 시작: {user_input[:50]}...")

            yield {
                "type": "progress",
                "stage": "router_analysis",
                "message": "사용자 의도를 분석하고 있습니다...",
                "progress": 0.1,
            }

            # 1단계: Router Agent - 의도 분석
            print(f"\n📍 [STEP 1] Router Agent 실행 중...")
            router_result = self.router_agent({"user_input": user_input})
            intent = router_result.get("intent", "unknown")
            print(f"   ✅ [ROUTER] 의도 분석 완료: {intent}")
            print(f"   📊 [ROUTER] 전체 결과: {router_result}")

            yield {
                "type": "progress",
                "stage": "planner_analysis",
                "message": f"실행 계획을 수립하고 있습니다... (의도: {intent})",
                "progress": 0.2,
                "intent": intent,
            }

            # 2단계: Enhanced Planner Agent - 하이브리드 실행 계획 수립
            print(f"\n📋 [STEP 2] Planner Agent 실행 중...")
            planner_input = {**router_result, "user_input": user_input}
            print(f"   📥 [PLANNER] 입력 데이터: {planner_input}")
            plan_result = self.planner_agent(planner_input)
            print(f"   ✅ [PLANNER] 계획 수립 완료")
            print(f"   📊 [PLANNER] 전체 결과: {plan_result}")

            execution_steps = plan_result.get("execution_steps", [])
            dependency_graph = plan_result.get("dependency_graph", {})

            print(f"   📋 [PLANNER] 실행 단계 수: {len(execution_steps)}")
            for i, step in enumerate(execution_steps):
                print(
                    f"      Step {i+1}: {step.get('step_id', 'unknown')} - {step.get('description', 'No description')[:50]}..."
                )

            yield {
                "type": "progress",
                "stage": "execution_start",
                "message": f"{len(execution_steps)}개 단계의 실행을 시작합니다...",
                "progress": 0.3,
                "steps_count": len(execution_steps),
            }

            # 3단계: 하이브리드 실행 (스트리밍)
            print(f"\n⚡ [STEP 3] 하이브리드 실행 시작 ({len(execution_steps)}개 단계)")
            execution_context = {
                "user_input": user_input,
                "intent": router_result.get("intent"),
                "key_entities": router_result.get("key_entities", []),
                "execution_steps": execution_steps,
                "execution_plan": execution_steps,
                "dependency_graph": dependency_graph,
            }

            # 단계별 실행을 스트리밍으로 처리
            execution_results = []
            for i, step in enumerate(execution_steps):
                step_progress = 0.3 + (0.5 * (i + 1) / len(execution_steps))
                step_id = step.get("step_id", f"step_{i+1}")
                step_description = step.get("description", "Unknown step")
                required_tools = step.get("required_tools", [])

                print(f"\n   🔄 [STEP 3.{i+1}] 단계 실행 시작: {step_id}")
                print(f"      📝 설명: {step_description}")
                print(f"      🛠️  필요 도구: {required_tools}")

                yield {
                    "type": "progress",
                    "stage": "step_execution",
                    "message": f"단계 {i+1}/{len(execution_steps)} 실행 중: {step_description}",
                    "progress": step_progress,
                    "current_step": step_id,
                }

                try:
                    # 단계 실행 (스트리밍 지원)
                    print(f"      🎯 [EXECUTION] 스트리밍 실행 시도...")
                    step_result = self._execute_step_streaming(step, execution_context)

                    if step_result:
                        print(f"      ✅ [EXECUTION] 스트리밍 실행 성공")
                        final_result = None
                        chunk_count = 0

                        for chunk in step_result:
                            chunk_count += 1
                            print(
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
                                final_result = {
                                    "step_id": step_id,
                                    "status": "success",
                                    "result": chunk.get("data", {}),
                                    "final_result": str(chunk.get("data", {}))[:500],
                                }
                                print(
                                    f"         ✅ [RESULT] 최종 결과 저장: {final_result['status']}"
                                )

                        if final_result:
                            execution_results.append(final_result)
                            print(
                                f"      ✅ [STEP 3.{i+1}] 완료 - 스트리밍 결과 저장됨"
                            )
                        else:
                            error_result = {
                                "step_id": step_id,
                                "status": "error",
                                "error": "스트리밍 실행 중 결과를 받지 못했습니다",
                            }
                            execution_results.append(error_result)
                            print(f"      ❌ [STEP 3.{i+1}] 실패 - 스트리밍 결과 없음")
                    else:
                        # 비스트리밍 실행
                        print(f"      🔄 [EXECUTION] 비스트리밍 실행 시도...")
                        result = self._execute_single_step(step, execution_context)
                        execution_results.append(result)
                        print(
                            f"      ✅ [STEP 3.{i+1}] 완료 - 비스트리밍 결과: {result.get('status', 'unknown')}"
                        )

                except Exception as e:
                    error_result = {
                        "step_id": step_id,
                        "status": "error",
                        "error": str(e),
                    }
                    execution_results.append(error_result)
                    print(f"      ❌ [STEP 3.{i+1}] 실행 실패: {str(e)}")

            print(
                f"\n   ✅ [STEP 3] 하이브리드 실행 완료: {len(execution_results)}개 결과"
            )
            for i, result in enumerate(execution_results):
                print(
                    f"      결과 {i+1}: {result.get('step_id', 'unknown')} - {result.get('status', 'unknown')}"
                )

            yield {
                "type": "progress",
                "stage": "trace_analysis",
                "message": "실행 결과를 분석하고 있습니다...",
                "progress": 0.8,
            }

            # 4단계: Trace Manager - 전체 추론 과정 분석
            print(f"\n📊 [STEP 4] Trace Manager 실행 중...")
            trace_analysis = self._analyze_execution_trace(
                execution_results, execution_context
            )
            print(
                f"   ✅ [TRACE] 분석 완료: {trace_analysis.get('final_assessment', {}).get('workflow_status', 'unknown')}"
            )

            yield {
                "type": "progress",
                "stage": "final_response",
                "message": "최종 응답을 생성하고 있습니다...",
                "progress": 0.9,
            }

            # 5단계: Answer Agent - 최종 응답 생성
            print(f"\n✨ [STEP 5] Answer Agent 실행 중...")
            final_response = self._generate_final_response(
                execution_results, trace_analysis, execution_context
            )
            print(f"   ✅ [ANSWER] 최종 응답 생성 완료")

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

            print(f"\n🎉 [ORCHESTRATOR] 스트리밍 처리 완료 ({total_time:.2f}초)")
            print(
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
            print(f"\n❌ [ORCHESTRATOR] 스트리밍 처리 중 오류: {str(e)}")
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

        print(f"         🎯 [STREAMING] 단계 타입: {step_type}, 도구: {required_tools}")

        # 슬라이드 생성 단계인 경우 스트리밍 지원
        if any(
            tool in required_tools
            for tool in ["slide_formatter", "format_slide", "slide_generator"]
        ):
            print(f"         🎨 [STREAMING] 슬라이드 생성 단계 감지")

            try:
                # LangChain SlideFormatter의 스트리밍 기능 직접 활용
                content = context.get("user_input", "클라우드 거버넌스 개요")

                # 사용자 입력에서 콘텐츠 정제
                if "슬라이드" in content or "slide" in content.lower():
                    content = (
                        content.replace("슬라이드", "").replace("slide", "").strip()
                    )
                    content = content or "클라우드 거버넌스 개요"

                slide_inputs = {
                    "content": content,
                    "title": "클라우드 거버넌스",
                    "slide_type": "basic",
                    "subtitle": "",
                    "format": "json",
                }

                print(f"         📋 [STREAMING] 슬라이드 입력: {slide_inputs}")

                # 스트리밍 실행
                print(f"         ▶️  [STREAMING] SlideFormatter 스트리밍 시작...")
                chunk_count = 0
                for chunk in self.slide_formatter.run_streaming(slide_inputs):
                    chunk_count += 1
                    print(
                        f"            📦 [SLIDE CHUNK {chunk_count}] {chunk.get('type', 'unknown')}: {chunk.get('message', '')}"
                    )
                    yield chunk

                print(
                    f"         ✅ [STREAMING] SlideFormatter 스트리밍 완료 ({chunk_count}개 청크)"
                )
                return

            except Exception as e:
                print(f"         ❌ [STREAMING] 슬라이드 생성 오류: {str(e)}")
                yield {
                    "type": "error",
                    "stage": "slide_generation_error",
                    "message": f"슬라이드 생성 중 오류: {str(e)}",
                    "progress": 0.0,
                    "error": str(e),
                }
                return

        # MCP 도구 실행이 필요한 경우
        elif any(
            tool in required_tools
            for tool in [
                "rag_retriever",
                "search_documents",
                "data_analyzer",
                "content_validator",
            ]
        ):
            print(f"         🔍 [STREAMING] MCP 도구 실행 필요 감지")

            try:
                # MCP 도구를 비동기로 실행하고 결과를 스트리밍 형태로 반환
                print(f"         🔧 [MCP] 비동기 MCP 도구 실행 시작...")

                # 진행 상황 스트리밍
                yield {
                    "type": "progress",
                    "stage": "mcp_tool_execution",
                    "message": "MCP 도구를 실행하고 있습니다...",
                    "progress": 0.3,
                }

                # 실제 MCP 도구 실행
                result = self._execute_single_step(step, context)

                print(
                    f"         ✅ [MCP] 도구 실행 완료: {result.get('status', 'unknown')}"
                )

                # 결과를 스트리밍 형태로 반환
                yield {
                    "type": "result",
                    "stage": "mcp_completed",
                    "message": "MCP 도구 실행이 완료되었습니다.",
                    "progress": 1.0,
                    "data": result,
                }
                return

            except Exception as e:
                print(f"         ❌ [MCP] 도구 실행 오류: {str(e)}")
                yield {
                    "type": "error",
                    "stage": "mcp_execution_error",
                    "message": f"MCP 도구 실행 중 오류: {str(e)}",
                    "progress": 0.0,
                    "error": str(e),
                }
                return

        # 스트리밍을 지원하지 않는 경우 None 반환
        print(f"         ⏭️  [STREAMING] 스트리밍 미지원 단계")
        return None

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

        print(f"      🔄 [SINGLE_STEP] 단계 실행 시작: {step_id}")
        print(f"         📝 설명: {step_description}")
        print(f"         🛠️  도구: {required_tools}")
        print(f"         📊 타입: {step_type}")

        try:
            # 도구 이름 정규화
            print(f"         🔧 [NORMALIZE] 도구 이름 정규화 시작...")
            normalized_tools = []
            for tool in required_tools:
                if tool in [
                    "rag_retriever",
                    "search_documents",
                    "data_analyzer",
                    "content_validator",
                ]:
                    normalized_tools.append("search_documents")
                    print(f"            ✅ '{tool}' → 'search_documents'")
                elif tool in ["slide_formatter", "format_slide", "slide_generator"]:
                    # 슬라이드 포맷팅은 LangChain Tool로 직접 처리
                    normalized_tools.append("slide_formatter_langchain")
                    print(f"            ✅ '{tool}' → 'slide_formatter_langchain'")
                elif tool in [
                    "report_summary",
                    "summarize_report",
                    "content_generator",
                ]:
                    normalized_tools.append("summarize_report")
                    print(f"            ✅ '{tool}' → 'summarize_report'")
                elif tool in ["get_tool_status"]:
                    normalized_tools.append("get_tool_status")
                    print(f"            ✅ '{tool}' → 'get_tool_status'")
                else:
                    normalized_tools.append("search_documents")
                    print(f"            ⚠️ '{tool}' → 'search_documents' (기본값)")

            print(f"         📋 [NORMALIZE] 정규화된 도구: {normalized_tools}")

            # LangChain Tool 직접 실행 (슬라이드 포맷팅)
            if "slide_formatter_langchain" in normalized_tools:
                print(f"         🎨 [LANGCHAIN] SlideFormatter 도구 직접 실행")

                # 사용자 입력에서 콘텐츠 추출
                user_input = context.get("user_input", "")
                if "슬라이드" in user_input or "slide" in user_input.lower():
                    content = (
                        user_input.replace("슬라이드", "").replace("slide", "").strip()
                    )
                    content = content or "클라우드 거버넌스 개요"
                else:
                    content = "클라우드 거버넌스 개요"

                slide_inputs = {
                    "content": content,
                    "title": "클라우드 거버넌스",
                    "slide_type": "basic",
                    "subtitle": "",
                    "format": "json",
                }

                print(f"            📋 [LANGCHAIN] 슬라이드 입력: {slide_inputs}")
                print(f"            ▶️  [LANGCHAIN] SlideFormatter 실행 중...")

                result = self.slide_formatter.run(slide_inputs)

                print(f"            ✅ [LANGCHAIN] SlideFormatter 실행 완료")
                print(f"            📊 [LANGCHAIN] 결과 타입: {type(result)}")

                return {
                    "step_id": step_id,
                    "step_type": step_type,
                    "tool": "slide_formatter_langchain",
                    "status": "success",
                    "result": result,
                    "final_result": str(result.get("html", ""))[:500],
                }

            # MCP 도구 실행 (단일 도구)
            elif len(normalized_tools) == 1 and normalized_tools[0] in [
                "search_documents",
                "summarize_report",
                "get_tool_status",
            ]:
                tool_name = normalized_tools[0]
                print(f"         🔧 [MCP] MCP 도구 실행: {tool_name}")

                # MCP 도구 실행을 위한 비동기 함수
                async def execute_mcp_tool():
                    try:
                        print(f"            🔗 [MCP] MCP 클라이언트 확인...")
                        if not self.mcp_multi_client:
                            raise Exception("MCP 클라이언트가 초기화되지 않았습니다")

                        print(f"            📋 [MCP] MCP 도구 목록 가져오는 중...")
                        # MCP 도구들 가져오기
                        tools = await self._get_mcp_tools()
                        print(f"            📊 [MCP] 사용 가능한 도구 수: {len(tools)}")

                        if tools:
                            tool_names = [tool.name for tool in tools]
                            print(f"            📋 [MCP] 도구 목록: {tool_names}")

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

                        print(
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

                                params = {"query": query, "top_k": 5}

                            print(
                                f"            📋 [MCP] search_documents 매개변수: {params}"
                            )
                            print(f"            ▶️  [MCP] search_documents 실행 중...")
                            result = await target_tool.ainvoke(params)
                            print(f"            ✅ [MCP] search_documents 실행 완료")

                        elif tool_name == "summarize_report":
                            params = step.get("parameters", {})
                            if not params:
                                params = {
                                    "content": context.get(
                                        "user_input", "클라우드 거버넌스 보고서"
                                    ),
                                    "title": "클라우드 거버넌스 보고서",
                                    "summary_type": "executive",
                                    "format_type": "html",
                                }

                            print(
                                f"            📋 [MCP] summarize_report 매개변수: {params}"
                            )
                            print(f"            ▶️  [MCP] summarize_report 실행 중...")
                            result = await target_tool.ainvoke(params)
                            print(f"            ✅ [MCP] summarize_report 실행 완료")

                        elif tool_name == "get_tool_status":
                            print(f"            ▶️  [MCP] get_tool_status 실행 중...")
                            result = await target_tool.ainvoke({})
                            print(f"            ✅ [MCP] get_tool_status 실행 완료")

                        print(f"            📊 [MCP] 결과 타입: {type(result)}")
                        print(
                            f"            📋 [MCP] 결과 미리보기: {str(result)[:200]}..."
                        )

                        return {
                            "step_id": step_id,
                            "step_type": step_type,
                            "tool": tool_name,
                            "status": "success",
                            "result": result,
                            "final_result": str(result)[:500],
                        }

                    except Exception as e:
                        print(f"            ❌ [MCP] 도구 실행 실패: {str(e)}")
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
                print(f"            🔄 [MCP] 비동기 실행 시작...")
                result = self._run_async_mcp_operation(execute_mcp_tool())
                print(
                    f"            ✅ [MCP] 비동기 실행 완료: {result.get('status', 'unknown')}"
                )
                return result

            else:
                # ReAct 실행기를 통한 실행 (복합 도구 또는 추론이 필요한 경우)
                print(f"         🤖 [REACT] ReAct Executor로 전달: {normalized_tools}")
                executor = self._get_or_create_executor(step_id)
                print(f"            📋 [REACT] Executor ID: {step_id}")
                print(f"            ▶️  [REACT] 실행 중...")
                result = executor.execute_step(step, context)
                print(
                    f"            ✅ [REACT] 실행 완료: {result.get('status', 'unknown')}"
                )
                return result

        except Exception as e:
            print(f"         ❌ [SINGLE_STEP] 단계 실행 실패: {str(e)}")
            import traceback

            traceback.print_exc()
            return {
                "step_id": step_id,
                "step_type": step_type,
                "tool": required_tools[0] if required_tools else "unknown",
                "status": "error",
                "error": str(e),
            }

    def _process_hybrid_execution(
        self,
        plan_result: Dict[str, Any],
        router_result: Dict[str, Any],
        user_input: str,
        start_time: float,
    ) -> Dict[str, Any]:
        """하이브리드 실행 방식 처리"""
        execution_steps = plan_result.get("execution_steps", [])
        dependency_graph = plan_result.get("dependency_graph", {})

        print(f"   └ 총 실행 단계: {len(execution_steps)}개")
        print(
            f"   └ 병렬 실행 가능: {len(dependency_graph.get('parallel_groups', []))}개 그룹"
        )

        # 3단계: 하이브리드 실행 (Plan & Execute + ReAct)
        print("\n🔄 3단계: 하이브리드 실행 (Plan & Execute + ReAct)")
        execution_context = {
            "user_input": user_input,
            "intent": router_result.get("intent"),
            "key_entities": router_result.get("key_entities", []),
            "execution_steps": execution_steps,  # 키 이름 수정!
            "execution_plan": execution_steps,  # 호환성을 위해 유지
            "dependency_graph": dependency_graph,
        }

        # 3단계: 하이브리드 실행 (단계별 실행)
        print("\n⚡ 3단계: 하이브리드 실행")
        execution_results = []

        for step in execution_steps:
            try:
                # 단계 실행 (스트리밍 지원 확인)
                step_result = self._execute_step_streaming(step, execution_context)
                if step_result:
                    # 스트리밍 지원하는 경우 - 마지막 결과만 수집
                    final_result = None
                    for chunk in step_result:
                        if chunk.get("type") == "result":
                            final_result = {
                                "step_id": step.get("step_id"),
                                "status": "success",
                                "result": chunk.get("data", {}),
                                "final_result": str(chunk.get("data", {}))[:500],
                            }

                    if final_result:
                        execution_results.append(final_result)
                    else:
                        # 스트리밍 실행 중 오류 발생
                        execution_results.append(
                            {
                                "step_id": step.get("step_id"),
                                "status": "error",
                                "error": "스트리밍 실행 중 결과를 받지 못했습니다",
                            }
                        )
                else:
                    # 비스트리밍 실행
                    result = self._execute_single_step(step, execution_context)
                    execution_results.append(result)

            except Exception as e:
                execution_results.append(
                    {
                        "step_id": step.get("step_id"),
                        "status": "error",
                        "error": str(e),
                    }
                )

        print(f"   ✅ 실행 완료: {len(execution_results)}개 단계")

        # 4단계: Trace Manager - 전체 추론 과정 분석
        print("\n📊 4단계: Trace Manager - 추론 과정 분석")
        trace_analysis = self._analyze_execution_trace(
            execution_results, execution_context
        )

        # 5단계: 실패 복구 처리 (필요시)
        if trace_analysis.get("final_assessment", {}).get("next_action") in [
            "retry",
            "revise",
        ]:
            print("\n🔧 5단계: 실패 복구 처리")
            recovery_result = self._handle_failure_recovery(
                execution_results, execution_context, trace_analysis
            )
            if recovery_result.get("recovery_status") == "success":
                execution_results = recovery_result.get(
                    "recovered_results", execution_results
                )

        # 6단계: Answer Agent - 최종 응답 생성
        print("\n✨ 6단계: Answer Agent - 최종 응답 생성")
        final_response = self._generate_final_response(
            execution_results, trace_analysis, execution_context
        )

        # 전체 처리 시간 계산
        total_time = time.time() - start_time

        # 최종 결과 구성
        final_result = {
            **final_response,
            "hybrid_execution_summary": {
                "total_execution_time": f"{total_time:.2f}초",
                "steps_executed": len(execution_results),
                "successful_steps": len(
                    [r for r in execution_results if r.get("status") == "success"]
                ),
                "reasoning_depth": trace_analysis.get("performance_metrics", {}).get(
                    "reasoning_depth", "medium"
                ),
                "overall_confidence": trace_analysis.get("final_assessment", {}).get(
                    "confidence", 0.5
                ),
            },
            "mcp_context": {
                **self.mcp_context,
                "processing_flow": [
                    f"Router: {router_result.get('intent', 'unknown')}",
                    f"Planner: {len(execution_steps)} steps planned",
                    f"Execution: {len(execution_results)} steps executed",
                    f"Trace Analysis: {trace_analysis.get('final_assessment', {}).get('workflow_status', 'unknown')}",
                    "Answer: completed",
                ],
                "status": "success",
                "hybrid_mode_used": True,
                "total_time": total_time,
            },
        }

        print(f"\n✅ 하이브리드 처리 완료 ({total_time:.2f}초)")
        return final_result

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

        # Answer Agent 입력 구성
        answer_input = {
            "agent_type": "hybrid_execution",
            "answer_content": answer_content,
            "execution_results": execution_results,
            "reasoning_trace": self.reasoning_trace_logger.get_global_trace(),
            "trace_summary": trace_analysis.get("trace_summary", {}),
            "overall_confidence": trace_analysis.get("final_assessment", {}).get(
                "confidence", 0.5
            ),
            "source_type": "hybrid_react",
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
                "slide_formatter_langchain": "available",
                "mcp_tools": mcp_tools_status,
            },
            "mcp_integration": {
                "multi_client_initialized": self.mcp_multi_client is not None,
                "legacy_client_available": self.mcp_client is not None,
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
        print("🧹 하이브리드 실행 상태 초기화 완료")
