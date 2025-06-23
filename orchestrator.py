from typing import Dict, Any, List
from agents import (
    RouterAgent,
    PlannerAgent,
    AnswerAgent,
    ReActExecutorAgent,
    TraceManagerAgent,
)
from tools import ReasoningTraceLogger, PlanRevisionTool, StateManager
import time


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

        # 하이브리드 모드 활성화 플래그
        self.hybrid_mode_enabled = True

        self.mcp_context = {
            "role": "hybrid_orchestrator",
            "function": "hybrid_workflow_coordination",
            "agents_initialized": True,
            "hybrid_mode": True,
        }

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

            # 하이브리드 모드 처리
            if (
                self.hybrid_mode_enabled
                and plan_result.get("execution_strategy") == "hybrid_react"
            ):
                return self._process_hybrid_execution(
                    plan_result, router_result, user_input, start_time
                )
            else:
                # 기존 방식 유지 (호환성)
                return self._process_legacy_execution(
                    plan_result, router_result, user_input, start_time
                )

        except Exception as e:
            error_time = time.time() - start_time
            print(f"\n❌ 하이브리드 오케스트레이터 오류: {str(e)}")
            return self._create_error_response(str(e), error_time)

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
            "execution_plan": execution_steps,
            "dependency_graph": dependency_graph,
        }

        execution_results = self._execute_hybrid_workflow(execution_context)

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

    def _process_legacy_execution(
        self,
        planner_result: Dict[str, Any],
        router_result: Dict[str, Any],
        user_input: str,
        start_time: float,
    ) -> Dict[str, Any]:
        """기존 방식 처리 (호환성 유지)"""
        selected_agent = planner_result.get("selected_agent", "DirectAnswer")
        print(f"   └ Legacy Mode - Selected Agent: {selected_agent}")

        # 3. Task Management Agent 실행
        agent_result = None
        if selected_agent in "TaskManagementAgent":
            print("🔧 Task Management Agent: 작업 처리 중...")
            agent_input = {**planner_result, "user_input": user_input}
            agent_result = self.task_management_agent(agent_input)
            print("   └ 작업 처리 완료")

        else:  # DirectAnswer
            print("💬 Direct Answer: 직접 응답 처리 중...")
            agent_result = {
                "agent_type": "direct",
                "answer_content": self._generate_direct_answer(user_input),
                "source_type": "direct",
                "confidence": "medium",
            }
            print("   └ 직접 응답 완료")

        # 4. Answer Agent - 최종 응답 정제
        print("✨ Answer Agent: 최종 응답 정제 중...")
        final_result = self.answer_agent(agent_result)
        print("   └ 최종 응답 준비 완료")

        # 전체 처리 시간 계산
        total_time = time.time() - start_time

        # 5. MCP Context 통합
        final_result["mcp_context"]["orchestrator"] = {
            **self.mcp_context,
            "processing_flow": [
                f"Router: {router_result.get('intent', 'unknown')}",
                f"Planner: {selected_agent}",
                f"Agent: {agent_result.get('agent_type', 'unknown')}",
                "Answer: completed",
            ],
            "status": "success",
            "hybrid_mode_used": False,
            "total_time": total_time,
        }

        print(f"✅ 레거시 처리 완료 ({total_time:.2f}초)")
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

    def _execute_hybrid_workflow(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """하이브리드 워크플로우 실행 (Plan & Execute + ReAct)"""
        execution_steps = context.get("execution_plan", [])

        if not execution_steps:
            return [{"status": "error", "message": "No execution steps provided"}]

        # 기본적으로 순차 실행 (병렬 실행은 향후 확장)
        execution_results = []

        for i, step in enumerate(execution_steps):
            print(f"   📝 단계 {i+1}/{len(execution_steps)}: {step['step_id']}")

            try:
                # ReAct Executor 생성 및 실행
                executor_id = f"step_{step['step_id']}"
                react_executor = self._get_or_create_executor(executor_id)

                execution_input = {"plan_step": step, "context": context}

                result = react_executor(execution_input)
                result["step_id"] = step["step_id"]
                result["step_type"] = step["step_type"]
                result["execution_method"] = "react"

                execution_results.append(result)
                print(f"   ✅ 단계 완료: {step['step_id']}")

            except Exception as e:
                error_result = {
                    "step_id": step["step_id"],
                    "status": "error",
                    "error": str(e),
                    "execution_method": "react",
                }
                execution_results.append(error_result)
                print(f"   ❌ 단계 실패: {step['step_id']} - {str(e)}")

        return execution_results

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
        return {
            "orchestrator": "hybrid_running",
            "agents": {
                "router": "initialized",
                "enhanced_planner": "initialized",
                "task_management": "legacy_support",
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
                "rag_retriever": "available",
                "slide_formatter": "available",
                "report_summary": "available",
            },
            "hybrid_features": {
                "parallel_execution": False,  # 향후 구현
                "react_reasoning": True,
                "failure_recovery": True,
                "trace_analysis": True,
                "hybrid_mode_enabled": self.hybrid_mode_enabled,
            },
            "mcp_context": self.mcp_context,
        }

    def set_hybrid_mode(self, enabled: bool):
        """하이브리드 모드 활성화/비활성화"""
        self.hybrid_mode_enabled = enabled
        self.mcp_context["hybrid_mode"] = enabled
        print(f"🔧 하이브리드 모드: {'활성화' if enabled else '비활성화'}")

    def clear_execution_state(self):
        """실행 상태 초기화"""
        self.executor_pool.clear()
        self.reasoning_trace_logger.clear_traces()
        self.plan_revision_tool.clear_history()
        self.state_manager.clear_all_states()
        print("🧹 하이브리드 실행 상태 초기화 완료")
