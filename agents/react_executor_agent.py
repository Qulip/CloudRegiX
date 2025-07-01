import json
import re
from typing import Dict, Any

from core import BaseAgent
from tools import ReasoningTraceLogger, StateManager, SlideFormatterTool
from mcp_client import get_mcp_client


class ReActExecutorAgent(BaseAgent):
    """
    ReAct 방식으로 개별 Plan Step을 실행하는 Agent
    Thought → Action → Observation 순환 실행
    """

    def __init__(self, executor_id: str = "react_executor"):
        super().__init__(f"ReActExecutorAgent_{executor_id}")
        self.executor_id = executor_id
        self.mcp_client = get_mcp_client()
        self.trace_logger = ReasoningTraceLogger()
        self.state_manager = StateManager()  # 상태 관리 도구
        self.slide_formatter = SlideFormatterTool()  # LangChain Tool 직접 사용
        self.max_iterations = 5  # 최대 ReAct 반복 횟수

    def execute_step(
        self, step: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ReAct 방식으로 개별 계획 단계 실행

        Args:
            step: 실행할 단계 정보
            context: 실행 컨텍스트

        Returns:
            실행 결과
        """
        step_id = step.get("step_id", "unknown")
        step_type = step.get("step_type", "general")
        description = step.get("description", "")
        required_tools = step.get("required_tools", [])

        print(f"🤖 ReAct Executor {self.executor_id} 시작: {step_id}")

        # ReAct 반복 실행
        for iteration in range(self.max_iterations):
            try:
                print(f"   🔄 반복 {iteration + 1}/{self.max_iterations}")

                # ReAct 입력 구성
                react_input = {
                    "plan_step": step,
                    "context": context,
                    "iteration": iteration,
                    "available_tools": required_tools,
                }

                # 🔥 핵심: LLM 호출 → postprocess에서 실제 도구 실행
                print(f"     💭 LLM 추론 시작...")
                react_result = self(
                    react_input
                )  # BaseAgent.__call__ → postprocess에서 도구 실행됨
                print(f"     💭 LLM 추론 및 도구 실행 완료")

                # 추론 결과 확인
                thought = react_result.get("thought", "")
                action = react_result.get("action", {})
                goal_achieved = react_result.get("goal_achieved", False)
                tool_execution_result = react_result.get("tool_execution_result", {})

                print(f"     🧠 Thought: {thought[:100]}...")
                print(f"     🎯 목표 달성: {goal_achieved}")
                print(
                    f"     🔧 도구 실행 상태: {tool_execution_result.get('status', 'none')}"
                )

                # Thought 및 Observation 기록
                self._log_trace("thought", thought, iteration, step_id)
                if tool_execution_result:
                    observation = f"도구 실행 결과: {tool_execution_result.get('status')} - {str(tool_execution_result)[:200]}..."
                    self._log_trace("observation", observation, iteration, step_id)

                # 목표 달성 체크 (도구 실행이 성공하고 goal_achieved가 True인 경우)
                if goal_achieved and tool_execution_result.get("status") == "success":
                    print(f"   ✅ 목표 달성 및 도구 실행 성공: {step_id}")
                    return {
                        "step_id": step_id,
                        "executor_id": self.executor_id,
                        "status": "success",
                        "iterations": iteration + 1,
                        "final_result": react_result.get("final_result", ""),
                        "confidence": react_result.get("confidence", 0.8),
                        "tool_results": tool_execution_result,
                        "react_trace": {
                            "thought": thought,
                            "action": action,
                            "observation": (
                                observation if "observation" in locals() else ""
                            ),
                        },
                    }

                # 부분 성공 체크 (도구는 실행됐지만 목표 달성하지 못한 경우)
                if (
                    tool_execution_result.get("status") == "success"
                    and not goal_achieved
                ):
                    print(f"   🔄 도구 실행 성공하지만 목표 미달성, 계속 진행...")
                    continue

                # 오류 발생 시 재시도 여부 체크
                if (
                    tool_execution_result.get("status") == "error"
                    and iteration < self.max_iterations - 1
                ):
                    print(
                        f"   ⚠️ 도구 실행 실패, 재시도: {tool_execution_result.get('error', '')}"
                    )
                    continue

                # 도구 실행이 없는 경우 (LLM이 도구를 제안하지 않음)
                if not tool_execution_result:
                    print(f"   ⚠️ 도구 실행이 없음, 재시도...")
                    continue

            except Exception as e:
                print(f"   ❌ 반복 {iteration + 1} 실행 실패: {str(e)}")
                if iteration == self.max_iterations - 1:
                    return {
                        "step_id": step_id,
                        "executor_id": self.executor_id,
                        "status": "error",
                        "iterations": iteration + 1,
                        "error": str(e),
                        "confidence": 0.0,
                    }

        # 최대 반복 횟수 도달
        print(f"   ⏰ 최대 반복 횟수 도달: {step_id}")
        return {
            "step_id": step_id,
            "executor_id": self.executor_id,
            "status": "partial_success",
            "iterations": self.max_iterations,
            "final_result": "최대 반복 횟수에 도달했습니다. 부분적 결과를 확인해주세요.",
            "confidence": 0.3,
        }

    def _log_trace(self, trace_type: str, content: str, iteration: int, step_id: str):
        """
        추론 과정 로깅

        Args:
            trace_type: "thought" | "observation"
            content: 로그 내용
            iteration: 반복 횟수
            step_id: 단계 ID
        """
        try:
            self.trace_logger.run(
                {
                    "agent_id": self.name,
                    "step_type": trace_type,
                    "content": content,
                    "step_index": iteration,
                    "metadata": {
                        "step_id": step_id,
                        "executor_id": self.executor_id,
                        "timestamp": self._get_timestamp(),
                    },
                }
            )
        except Exception as e:
            print(f"     ⚠️ 로그 기록 실패: {str(e)}")

    def _get_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime

        return datetime.now().isoformat()

    def preprocess(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        ReAct 실행을 위한 전처리
        """
        # 실행 상태 초기화
        self.state_manager.run(
            {
                "action": "set_state",
                "agent_id": self.name,
                "data": {
                    "status": "starting",
                    "step_index": 0,
                    "current_action": "preprocessing",
                    "progress": 0.0,
                },
            }
        )

        return inputs

    def _create_prompt(self, inputs: Dict[str, Any]) -> str:
        """
        ReAct 실행을 위한 프롬프트 생성
        """
        plan_step = inputs.get("plan_step", {})
        context = inputs.get("context", {})
        iteration = inputs.get("iteration", 0)
        available_tools = inputs.get(
            "available_tools", ["search_documents", "format_slide", "summarize_report"]
        )

        step_id = plan_step.get("step_id", "unknown")
        step_type = plan_step.get("step_type", "general")
        description = plan_step.get("description", "Execute the given step")

        # 사용 가능한 도구 목록 생성
        tool_descriptions = {
            "search_documents": "RAG 기반 문서 검색 (매개변수: query, top_k)",
            "rag_retriever": "RAG 기반 문서 검색 (매개변수: query, top_k)",
            "format_slide": "슬라이드 포맷팅 - LangChain Tool (매개변수: content, title, slide_type, subtitle, format_type)",
            "slide_formatter": "슬라이드 포맷팅 - LangChain Tool (매개변수: content, title, slide_type, subtitle, format_type)",
            "summarize_report": "보고서 요약 (매개변수: content, title, summary_type, format_type)",
            "report_summary": "보고서 요약 (매개변수: content, title, summary_type, format_type)",
            "get_tool_status": "도구 상태 확인 (매개변수 없음)",
        }

        available_tool_info = []
        for tool in available_tools:
            if tool in tool_descriptions:
                available_tool_info.append(f"- {tool}: {tool_descriptions[tool]}")

        prompt = f"""
당신은 클라우드 거버넌스 AI 시스템의 ReAct Executor Agent입니다.
주어진 계획 단계를 ReAct (Reasoning and Acting) 방식으로 실행해야 합니다.

**현재 실행 중인 단계:**
- 단계 ID: {step_id}
- 단계 유형: {step_type}
- 설명: {description}
- 현재 반복: {iteration + 1}/{self.max_iterations}

**사용 가능한 도구들:**
{chr(10).join(available_tool_info)}

**단계 유형별 권장 도구:**
- data_collection: search_documents (RAG 검색)
- analysis: search_documents + summarize_report  
- generation: format_slide (LangChain Tool) 또는 summarize_report
- validation: search_documents (검증용 정보 수집)
- formatting: format_slide (LangChain Tool)

**출력 형식 (JSON):**
{{
    "thought": "현재 상황 분석 및 다음 행동 계획. 단계 유형과 설명을 고려하여 적절한 도구를 선택하세요.",
    "action": {{
        "tool_name": "search_documents|format_slide|summarize_report|get_tool_status",
        "tool_params": {{
            "query": "검색할 내용 (search_documents용)",
            "content": "처리할 내용 (format_slide, summarize_report용)",
            "title": "제목",
            "top_k": 5
        }}
    }},
    "goal_achieved": true/false,
    "confidence": 0.0-1.0,
    "final_result": "목표 달성 시 최종 결과 설명",
    "status": "success|partial_success|error"
}}

**중요한 지침:**
1. 단계 유형({step_type})에 맞는 적절한 도구를 선택하세요
2. format_slide/slide_formatter는 이제 LangChain Tool로 직접 실행됩니다
3. 이전 반복에서 오류가 있었다면 다른 접근법을 시도하세요  
4. 충분한 정보를 얻었다면 goal_achieved를 true로 설정하세요
5. tool_params는 선택한 도구에 맞는 매개변수만 포함하세요

정확한 JSON 형식으로만 응답하세요.
"""
        return prompt

    def postprocess(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        ReAct 실행 결과 후처리 - LLM 응답 파싱 및 실제 도구 실행
        """
        try:
            # LLM 응답에서 JSON 파싱 (다른 에이전트들과 동일한 방식)
            content = outputs.content if hasattr(outputs, "content") else str(outputs)

            # JSON 부분 추출
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # 필수 필드 보완
                result["executor_id"] = self.executor_id
                result["agent_name"] = self.name
                result["status"] = result.get("status", "success")

                # 🔥 핵심: 여기서 실제 도구 실행 (MCP 또는 LangChain Tool)
                action = result.get("action", {})
                if action and action.get("tool_name"):
                    print(f"     🚀 LLM이 제안한 도구 실행: {action.get('tool_name')}")
                    try:
                        # 도구 실행 (MCP 또는 LangChain Tool)
                        tool_result = self._execute_tool(action)
                        result["tool_execution_result"] = tool_result
                        result["observation"] = (
                            f"도구 실행 완료: {tool_result.get('status', 'unknown')}"
                        )

                        # 도구 실행 성공 시 goal_achieved 업데이트
                        if tool_result.get("status") == "success":
                            result["goal_achieved"] = True
                            if "result" in tool_result:
                                # 도구 결과를 final_result로 포함
                                result["final_result"] = (
                                    str(tool_result["result"])[:500] + "..."
                                )

                        print(f"     ✅ 도구 실행 성공: {action.get('tool_name')}")
                    except Exception as tool_error:
                        print(f"     ❌ 도구 실행 실패: {str(tool_error)}")
                        result["tool_execution_result"] = {
                            "status": "error",
                            "error": str(tool_error),
                        }
                        result["observation"] = f"도구 실행 실패: {str(tool_error)}"
                        result["goal_achieved"] = False

                # 상태 업데이트
                self.state_manager.run(
                    {
                        "action": "set_state",
                        "agent_id": self.name,
                        "data": {
                            "status": "completed",
                            "final_result": result.get("final_result", ""),
                            "confidence": result.get("confidence", 0.5),
                            "goal_achieved": result.get("goal_achieved", False),
                        },
                    }
                )

                return result
            else:
                # JSON 파싱 실패 시 기본 응답
                return {
                    "status": "error",
                    "error": "JSON 파싱 실패",
                    "executor_id": self.executor_id,
                    "agent_name": self.name,
                    "confidence": 0.0,
                    "goal_achieved": False,
                    "final_result": "응답 파싱에 실패했습니다.",
                    "thought": "응답 파싱 실패",
                    "action": {"tool_name": "none", "tool_params": {}},
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"후처리 중 오류 발생: {str(e)}",
                "executor_id": self.executor_id,
                "agent_name": self.name,
                "confidence": 0.0,
                "goal_achieved": False,
                "final_result": f"처리 중 오류가 발생했습니다: {str(e)}",
                "thought": f"오류 발생: {str(e)}",
                "action": {"tool_name": "none", "tool_params": {}},
            }

    def _execute_tool(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        실제 도구 실행 (MCP 또는 LangChain Tool)

        Args:
            action: LLM이 제안한 액션 {"tool_name": "...", "tool_params": {...}}

        Returns:
            도구 실행 결과
        """
        try:
            tool_name = action.get("tool_name", "")
            tool_params = action.get("tool_params", {})

            print(f"       🔧 도구 실제 호출: {tool_name}")
            print(f"       📋 매개변수: {tool_params}")

            # 슬라이드 포맷팅은 LangChain Tool로 실행
            if tool_name == "slide_formatter" or tool_name == "format_slide":
                print(f"       🎨 LangChain SlideFormatter 도구 실행")
                content = tool_params.get("content", "")
                if not content:
                    content = "클라우드 거버넌스 개요"  # 기본 콘텐츠
                title = tool_params.get("title", "클라우드 거버넌스")
                slide_type = tool_params.get("slide_type", "basic")
                subtitle = tool_params.get("subtitle", "")
                format_type = tool_params.get("format_type", "json")

                # LangChain Tool 직접 실행
                result = self.slide_formatter.run(
                    {
                        "content": content,
                        "title": title,
                        "slide_type": slide_type,
                        "subtitle": subtitle,
                        "format": format_type,
                    }
                )

                print(f"       ✅ LangChain SlideFormatter 실행 성공")
                return {
                    "status": "success",
                    "tool_name": tool_name,
                    "tool_type": "langchain",
                    "tool_params": tool_params,
                    "result": result,
                    "data_size": len(str(result)) if result else 0,
                }

            # 다른 도구들은 MCP를 통해 실행
            elif tool_name == "rag_retriever" or tool_name == "search_documents":
                print(f"       🔍 MCP 문서 검색 도구 실행")
                query = tool_params.get("query", tool_params.get("content", ""))
                if not query:
                    query = "클라우드 거버넌스"  # 기본 쿼리
                top_k = tool_params.get("top_k", 5)
                result = self.mcp_client.search_documents(query=query, top_k=top_k)

            elif tool_name == "report_summary" or tool_name == "summarize_report":
                print(f"       📊 MCP 보고서 요약 도구 실행")
                content = tool_params.get("content", "")
                if not content:
                    content = "클라우드 거버넌스 보고서"  # 기본 콘텐츠
                title = tool_params.get("title", "클라우드 거버넌스 보고서")
                summary_type = tool_params.get("summary_type", "executive")
                format_type = tool_params.get("format_type", "html")

                result = self.mcp_client.summarize_report(
                    content=content,
                    title=title,
                    summary_type=summary_type,
                    format_type=format_type,
                )

            elif tool_name == "get_tool_status":
                print(f"       📈 MCP 도구 상태 확인")
                result = self.mcp_client.get_tool_status()

            else:
                # 알려지지 않은 도구
                print(f"       ❓ 알려지지 않은 도구: {tool_name}")
                return {
                    "status": "error",
                    "error": f"알려지지 않은 도구: {tool_name}",
                    "available_tools": [
                        "search_documents",
                        "format_slide (LangChain)",
                        "summarize_report",
                        "get_tool_status",
                    ],
                }

            # MCP 결과 처리
            if "error" in result:
                print(f"       ❌ MCP 도구 실행 실패: {result.get('error', '')}")
                return {
                    "status": "error",
                    "error": result.get("error", "도구 실행 실패"),
                    "tool_name": tool_name,
                    "tool_type": "mcp",
                    "tool_params": tool_params,
                }
            else:
                print(f"       ✅ MCP 도구 실행 성공: {tool_name}")
                print(f"       📊 결과 크기: {len(str(result))} 문자")
                return {
                    "status": "success",
                    "tool_name": tool_name,
                    "tool_type": "mcp",
                    "tool_params": tool_params,
                    "result": result,
                    "data_size": len(str(result)) if result else 0,
                }

        except Exception as e:
            print(f"       💥 도구 실행 예외: {str(e)}")
            return {
                "status": "error",
                "error": f"도구 실행 중 예외 발생: {str(e)}",
                "tool_name": action.get("tool_name", "unknown"),
                "exception_type": type(e).__name__,
            }
