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
        개별 단계를 스트리밍으로 실행 (모든 실행을 ReAct Executor로 위임)

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

        # 모든 스트리밍 실행을 ReAct Executor로 위임
        logger.info(f"         🤖 [STREAMING] 모든 스트리밍을 ReAct Executor로 위임")
        yield from self._execute_react_streaming(step, context)

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
        개별 단계 실행 (모든 도구 실행을 ReAct Executor로 위임)

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
            # 모든 도구 실행을 ReAct Executor로 위임
            logger.info(f"         🤖 [REACT] 모든 도구 실행을 ReAct Executor로 위임")
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
