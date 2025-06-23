from typing import Dict, Any, List
from datetime import datetime
from core import BaseTool


class ReasoningTraceLogger(BaseTool):
    """
    ReAct 추론 과정을 기록하고 관리하는 Tool
    각 Agent의 Thought, Action, Observation을 추적
    """

    def __init__(self):
        self.traces = {}  # agent_id별 trace 저장
        self.global_trace = []  # 전체 워크플로우 trace

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        추론 과정 기록

        Args:
            inputs: {
                "agent_id": str,
                "step_type": "thought|action|observation",
                "content": str,
                "step_index": int,
                "metadata": dict
            }

        Returns:
            기록 결과
        """
        try:
            agent_id = inputs.get("agent_id", "unknown")
            step_type = inputs.get("step_type", "unknown")
            content = inputs.get("content", "")
            step_index = inputs.get("step_index", 0)
            metadata = inputs.get("metadata", {})

            # Trace 항목 생성
            trace_entry = {
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "step_type": step_type,
                "step_index": step_index,
                "content": content,
                "metadata": metadata,
            }

            # Agent별 trace 저장
            if agent_id not in self.traces:
                self.traces[agent_id] = []
            self.traces[agent_id].append(trace_entry)

            # 글로벌 trace에도 추가
            self.global_trace.append(trace_entry)

            return {
                "status": "success",
                "trace_id": f"{agent_id}_{step_index}_{step_type}",
                "total_steps": len(self.traces.get(agent_id, [])),
                "global_step_count": len(self.global_trace),
            }

        except Exception as e:
            return {"status": "error", "message": str(e), "trace_id": None}

    def get_agent_trace(self, agent_id: str) -> List[Dict[str, Any]]:
        """특정 Agent의 trace 반환"""
        return self.traces.get(agent_id, [])

    def get_global_trace(self) -> List[Dict[str, Any]]:
        """전체 워크플로우 trace 반환"""
        return self.global_trace

    def get_reasoning_summary(self, agent_id: str = None) -> Dict[str, Any]:
        """추론 과정 요약 생성"""
        if agent_id:
            traces = self.traces.get(agent_id, [])
        else:
            traces = self.global_trace

        thoughts = [t for t in traces if t["step_type"] == "thought"]
        actions = [t for t in traces if t["step_type"] == "action"]
        observations = [t for t in traces if t["step_type"] == "observation"]

        return {
            "total_steps": len(traces),
            "thought_count": len(thoughts),
            "action_count": len(actions),
            "observation_count": len(observations),
            "reasoning_chain": [
                {
                    "step": i + 1,
                    "type": trace["step_type"],
                    "content": (
                        trace["content"][:100] + "..."
                        if len(trace["content"]) > 100
                        else trace["content"]
                    ),
                }
                for i, trace in enumerate(traces)
            ],
        }

    def clear_traces(self, agent_id: str = None):
        """Trace 초기화"""
        if agent_id:
            self.traces[agent_id] = []
        else:
            self.traces = {}
            self.global_trace = []
