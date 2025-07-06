import json
import re
from typing import Dict, Any, List
from datetime import datetime

from core import BaseAgent


class PlannerAgent(BaseAgent):
    """
    Planner Agent
    Router Agent의 결과를 바탕으로 어떤 작업을 수행할지 결정
    Task Management Agent에 전달할 작업 타입 결정
    """

    def __init__(self):
        super().__init__("PlannerAgent")
        self.mcp_context = {"role": "planner", "function": "task_planning"}

    def _create_prompt(self, inputs: Dict[str, Any]) -> str:
        """
        하이브리드 실행 계획 수립을 위한 프롬프트 생성

        Args:
            inputs (Dict[str, Any]): Router Agent 결과 포함

        Returns:
            str: LLM용 프롬프트
        """
        # Router Agent 결과 추출
        intent = inputs.get("intent", "general")
        confidence = inputs.get("confidence", 0.0)
        key_entities = inputs.get("key_entities", [])
        user_input = inputs.get("user_input", "")

        # 현재 의도를 인스턴스 변수에 저장 (검증 시 사용)
        self._current_intent = intent

        prompt = f"""
당신은 클라우드 거버넌스 AI 시스템의 Enhanced Planner Agent입니다.
Router Agent의 분석 결과를 바탕으로 하이브리드 실행 계획을 수립해야 합니다.

**Router Agent 분석 결과:**
- Intent: {intent}
- Confidence: {confidence}
- Key Entities: {key_entities}
- Original Input: {user_input}

**중요: 의도별 실행 계획 가이드라인:**

1. **intent가 "question" 또는 "general"인 경우:**
   - 슬라이드 생성 관련 단계(drafting, generating)는 포함하지 않음
   - slide_draft, slide_generator 도구는 사용하지 않음
   - data_collection과 analysis 단계만 사용
   - 간단한 질문 답변에 집중

2. **intent가 "slide_generation"인 경우:**
   - 전체 슬라이드 생성 파이프라인 사용
   - data_collection → analysis → drafting → generating 순서
   - 모든 슬라이드 관련 도구 사용 가능

**하이브리드 실행 전략:**
1. 전체적인 coarse-grained plan 수립
2. 각 단계별로 ReAct Executor 할당
3. 병렬/순차 실행 결정
4. 실패 복구 전략 포함

**실행 단계 유형:**
- "data_collection": RAG 기반 정보 수집
- "analysis": 수집된 데이터 분석
- "drafting": 슬라이드 초안 작성 (slide_generation intent에만 사용)
- "validation": 결과 검증
- "generating": 최종 슬라이드 결과물 생성 (slide_generation intent에만 사용)

**사용 가능한 도구들:**
- "rag_retriever": RAG 기반 문서 검색 (MCP 도구명: search_documents)
- "slide_draft": 슬라이드 초안 생성 (MCP 도구명: create_slide_draft) - slide_generation intent에만 사용
- "slide_generator": 최종 슬라이드 생성 (LangChain Tool) - slide_generation intent에만 사용
- "report_summary": 보고서 요약 (MCP 도구명: summarize_report)
- "get_tool_status": 도구 상태 확인

**의도별 권장 실행 계획:**

Intent가 "question" 또는 "general"인 경우:
- data_collection: ["rag_retriever"]
- analysis: ["rag_retriever", "report_summary"]

Intent가 "slide_generation"인 경우:
- data_collection: ["rag_retriever"]
- analysis: ["rag_retriever", "report_summary"]
- drafting: ["slide_draft"]
- validation: ["rag_retriever"]
- generating: ["slide_generator"]

**출력 형식 (JSON):**
{{
    "execution_strategy": "hybrid_react",
    "overall_plan": {{
        "intent_type": "{intent}",
        "complexity": "simple|medium|complex",
        "estimated_steps": 3,
        "parallel_execution": true/false
    }},
    "execution_steps": [
        {{
            "step_id": "step_1",
            "step_type": "data_collection|analysis|drafting|validation|generating",
            "description": "단계 설명",
            "required_tools": ["rag_retriever", "slide_generator"],
            "depends_on": [],
            "priority": "high|medium|low",
            "timeout": 30,
            "retry_enabled": true
        }}
    ],
    "failure_recovery": {{
        "auto_retry": true,
        "max_retries": 2,
        "fallback_strategy": "simplify|alternative_path|manual_intervention"
    }},
    "success_criteria": {{
        "min_step_success_rate": 0.8,
        "overall_confidence_threshold": 0.7,
        "max_execution_time": 300
    }},
    "mcp_context": {{"role": "enhanced_planner", "status": "success"}}
}}

정확한 JSON 형식으로만 응답하세요.
"""
        return prompt

    def postprocess(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced Planner Agent 출력 후처리

        Args:
            outputs (Dict[str, Any]): LLM 응답

        Returns:
            Dict[str, Any]: 후처리된 결과
        """
        try:
            # LLM 응답에서 JSON 파싱
            content = outputs.content if hasattr(outputs, "content") else str(outputs)

            # JSON 부분 추출
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # 실행 계획 검증 및 보완
                execution_steps = result.get("execution_steps", [])
                validated_steps = self._validate_execution_steps(execution_steps)
                result["execution_steps"] = validated_steps

                # 의존성 체크
                dependency_graph = self._build_dependency_graph(validated_steps)
                result["dependency_graph"] = dependency_graph

                # MCP context 업데이트
                result["mcp_context"] = {
                    **self.mcp_context,
                    "status": "success",
                    "execution_strategy": result.get(
                        "execution_strategy", "hybrid_react"
                    ),
                    "total_steps": len(validated_steps),
                    "planning_timestamp": self._get_timestamp(),
                }

                return result
            else:
                # JSON 파싱 실패 시 기본 응답
                return self._create_fallback_plan()

        except Exception as e:
            return self._create_error_plan(str(e))

    def _validate_execution_steps(
        self, steps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """실행 단계 검증 및 보완"""
        validated_steps = []

        # 도구 이름 매핑 (잘못된 도구명 → 올바른 도구명)
        tool_mapping = {
            "search_documents": "rag_retriever",
            "text_analyzer": "rag_retriever",
            "slide_formatter": "slide_draft",
            "validator": "rag_retriever",
            "summarize_report": "report_summary",
        }

        # 단계 유형별 기본 도구
        default_tools_by_type = {
            "data_collection": ["rag_retriever"],
            "analysis": ["rag_retriever"],
            "drafting": ["slide_draft"],
            "validation": ["rag_retriever"],
            "generating": ["slide_generator"],
        }

        # 현재 처리 중인 의도 확인 (mcp_context에서 가져오기)
        current_intent = getattr(self, "_current_intent", "general")

        for i, step in enumerate(steps):
            # 기본 필드 설정
            step_type = step.get("step_type", "general")
            required_tools = step.get("required_tools", [])

            # 의도에 따른 단계 필터링
            if current_intent in ["question", "general"]:
                # 일반 질문인 경우 슬라이드 생성 관련 단계 제외
                if step_type in ["drafting", "generating"]:
                    print(f"   🚫 일반 질문이므로 슬라이드 생성 단계 제외: {step_type}")
                    continue

                # 슬라이드 생성 도구 제외
                required_tools = [
                    tool
                    for tool in required_tools
                    if tool not in ["slide_draft", "slide_generator"]
                ]

            # 도구 이름 검증 및 매핑
            validated_tools = []
            for tool in required_tools:
                if tool in tool_mapping:
                    validated_tools.append(tool_mapping[tool])
                elif tool in [
                    "rag_retriever",
                    "slide_draft",
                    "slide_generator",
                    "report_summary",
                    "get_tool_status",
                ]:
                    # 일반 질문인 경우 슬라이드 생성 도구 제외
                    if current_intent in ["question", "general"] and tool in [
                        "slide_draft",
                        "slide_generator",
                    ]:
                        continue
                    validated_tools.append(tool)
                else:
                    # 알려지지 않은 도구는 단계 유형에 따라 기본 도구로 대체
                    if step_type in default_tools_by_type:
                        default_tools = default_tools_by_type[step_type]
                        # 일반 질문인 경우 슬라이드 생성 도구 제외
                        if current_intent in ["question", "general"]:
                            default_tools = [
                                tool
                                for tool in default_tools
                                if tool not in ["slide_draft", "slide_generator"]
                            ]
                        validated_tools.extend(default_tools)

            # 도구가 없는 경우 단계 유형에 따라 기본 도구 설정
            if not validated_tools and step_type in default_tools_by_type:
                default_tools = default_tools_by_type[step_type]
                # 일반 질문인 경우 슬라이드 생성 도구 제외
                if current_intent in ["question", "general"]:
                    default_tools = [
                        tool
                        for tool in default_tools
                        if tool not in ["slide_draft", "slide_generator"]
                    ]
                validated_tools = default_tools

            # 최종 검증된 단계
            # 빈 도구 리스트인 경우 기본 도구 설정
            if not validated_tools:
                validated_tools = ["rag_retriever"]  # 최소한 기본 도구는 설정

            validated_step = {
                "step_id": step.get("step_id", f"step_{i+1}"),
                "step_type": step_type,
                "description": step.get("description", f"Execute step {i+1}"),
                "required_tools": validated_tools,
                "depends_on": step.get("depends_on", []),
                "priority": step.get("priority", "medium"),
                "timeout": step.get("timeout", 60),
                "retry_enabled": step.get("retry_enabled", True),
                "max_retries": step.get("max_retries", 2),
            }
            validated_steps.append(validated_step)

        return validated_steps

    def _build_dependency_graph(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """의존성 그래프 구성"""
        graph = {
            "nodes": [step["step_id"] for step in steps],
            "edges": [],
            "parallel_groups": [],
            "sequential_order": [],
        }

        # 의존성 엣지 생성
        for step in steps:
            step_id = step["step_id"]
            depends_on = step.get("depends_on", [])

            for dependency in depends_on:
                graph["edges"].append({"from": dependency, "to": step_id})

        # 병렬 실행 가능한 그룹 식별
        independent_steps = [
            step["step_id"] for step in steps if not step.get("depends_on", [])
        ]

        if len(independent_steps) > 1:
            graph["parallel_groups"].append(independent_steps)

        # 순차 실행 순서 결정
        remaining_steps = [step["step_id"] for step in steps]
        execution_order = []

        while remaining_steps:
            # 의존성이 해결된 단계들 찾기
            ready_steps = []
            for step_id in remaining_steps:
                step = next(s for s in steps if s["step_id"] == step_id)
                dependencies = step.get("depends_on", [])

                if all(dep in execution_order for dep in dependencies):
                    ready_steps.append(step_id)

            if ready_steps:
                execution_order.extend(ready_steps)
                for step_id in ready_steps:
                    remaining_steps.remove(step_id)
            else:
                # 순환 의존성이나 오류 상황
                execution_order.extend(remaining_steps)
                break

        graph["sequential_order"] = execution_order

        return graph

    def _create_fallback_plan(self) -> Dict[str, Any]:
        """기본 대체 계획 생성"""
        current_intent = getattr(self, "_current_intent", "general")

        # 의도에 따른 기본 계획 생성
        if current_intent == "slide_generation":
            execution_steps = [
                {
                    "step_id": "fallback_data_collection",
                    "step_type": "data_collection",
                    "description": "기본 데이터 수집",
                    "required_tools": ["rag_retriever"],
                    "depends_on": [],
                    "priority": "medium",
                    "timeout": 60,
                    "retry_enabled": True,
                },
                {
                    "step_id": "fallback_slide_generation",
                    "step_type": "generating",
                    "description": "기본 슬라이드 생성",
                    "required_tools": ["slide_generator"],
                    "depends_on": ["fallback_data_collection"],
                    "priority": "medium",
                    "timeout": 120,
                    "retry_enabled": True,
                },
            ]
        else:
            # 일반 질문인 경우 슬라이드 생성 단계 제외
            execution_steps = [
                {
                    "step_id": "fallback_step",
                    "step_type": "data_collection",
                    "description": "기본 정보 수집 및 분석",
                    "required_tools": ["rag_retriever"],
                    "depends_on": [],
                    "priority": "medium",
                    "timeout": 60,
                    "retry_enabled": True,
                }
            ]

        return {
            "execution_strategy": "hybrid_react",
            "overall_plan": {
                "intent_type": current_intent,
                "complexity": "simple",
                "estimated_steps": len(execution_steps),
                "parallel_execution": False,
            },
            "execution_steps": execution_steps,
            "failure_recovery": {
                "auto_retry": True,
                "max_retries": 1,
                "fallback_strategy": "manual_intervention",
            },
            "success_criteria": {
                "min_step_success_rate": 0.5,
                "overall_confidence_threshold": 0.5,
                "max_execution_time": 120,
            },
            "dependency_graph": {
                "nodes": ["fallback_step"],
                "edges": [],
                "parallel_groups": [],
                "sequential_order": ["fallback_step"],
            },
            "mcp_context": {
                **self.mcp_context,
                "status": "fallback",
                "message": "JSON 파싱 실패로 기본 계획 적용",
            },
        }

    def _create_error_plan(self, error_message: str) -> Dict[str, Any]:
        """오류 상황을 위한 계획 생성"""
        return {
            "execution_strategy": "error_recovery",
            "overall_plan": {
                "intent_type": "error",
                "complexity": "simple",
                "estimated_steps": 1,
                "parallel_execution": False,
            },
            "execution_steps": [
                {
                    "step_id": "error_handling",
                    "step_type": "validation",
                    "description": f"Handle planning error: {error_message}",
                    "required_tools": ["reasoning_trace_logger"],
                    "depends_on": [],
                    "priority": "high",
                    "timeout": 30,
                    "retry_enabled": False,
                }
            ],
            "failure_recovery": {
                "auto_retry": False,
                "max_retries": 0,
                "fallback_strategy": "manual_intervention",
            },
            "success_criteria": {
                "min_step_success_rate": 1.0,
                "overall_confidence_threshold": 0.3,
                "max_execution_time": 60,
            },
            "mcp_context": {
                **self.mcp_context,
                "status": "error",
                "message": error_message,
            },
        }

    def _get_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        return datetime.now().isoformat()
