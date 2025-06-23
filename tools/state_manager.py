from typing import Dict, Any, List
from datetime import datetime
from core import BaseTool


class StateManager(BaseTool):
    """
    Agent 실행 상태 및 공유 데이터 관리 Tool
    병렬 실행 시 상태 동기화 및 의존성 관리
    """

    def __init__(self):
        self.agent_states = {}  # Agent별 상태 저장
        self.shared_data = {}  # 공유 데이터 저장소
        self.dependencies = {}  # Agent 간 의존성 관리
        self.execution_order = []  # 실행 순서 기록

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        상태 관리 작업 실행

        Args:
            inputs: {
                "action": "set_state|get_state|set_shared|get_shared|check_dependency",
                "agent_id": str,
                "data": Dict,
                "key": str (for shared data),
                "depends_on": List[str] (for dependencies)
            }

        Returns:
            작업 결과
        """
        try:
            action = inputs.get("action", "get_state")
            agent_id = inputs.get("agent_id", "unknown")

            if action == "set_state":
                return self._set_agent_state(agent_id, inputs.get("data", {}))

            elif action == "get_state":
                return self._get_agent_state(agent_id)

            elif action == "set_shared":
                return self._set_shared_data(
                    inputs.get("key", ""), inputs.get("data", {})
                )

            elif action == "get_shared":
                return self._get_shared_data(inputs.get("key", ""))

            elif action == "check_dependency":
                return self._check_dependencies(agent_id, inputs.get("depends_on", []))

            elif action == "register_dependency":
                return self._register_dependency(agent_id, inputs.get("depends_on", []))

            elif action == "complete_execution":
                return self._complete_execution(agent_id, inputs.get("result", {}))

            else:
                return {"status": "error", "message": f"Unknown action: {action}"}

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "action": inputs.get("action", "unknown"),
            }

    def _set_agent_state(
        self, agent_id: str, state_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Agent 상태 설정"""
        timestamp = datetime.now().isoformat()

        if agent_id not in self.agent_states:
            self.agent_states[agent_id] = {"created_at": timestamp, "states": []}

        # 새로운 상태 추가
        new_state = {
            "timestamp": timestamp,
            "status": state_data.get("status", "running"),
            "step_index": state_data.get("step_index", 0),
            "current_action": state_data.get("current_action", ""),
            "data": state_data.get("data", {}),
            "progress": state_data.get("progress", 0.0),
        }

        self.agent_states[agent_id]["states"].append(new_state)
        self.agent_states[agent_id]["last_updated"] = timestamp
        self.agent_states[agent_id]["current_status"] = new_state["status"]

        return {
            "status": "success",
            "agent_id": agent_id,
            "state_count": len(self.agent_states[agent_id]["states"]),
            "current_status": new_state["status"],
        }

    def _get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Agent 상태 조회"""
        if agent_id not in self.agent_states:
            return {
                "status": "not_found",
                "agent_id": agent_id,
                "message": "Agent state not found",
            }

        agent_state = self.agent_states[agent_id]
        current_state = agent_state["states"][-1] if agent_state["states"] else {}

        return {
            "status": "success",
            "agent_id": agent_id,
            "current_state": current_state,
            "total_states": len(agent_state["states"]),
            "created_at": agent_state.get("created_at"),
            "last_updated": agent_state.get("last_updated"),
        }

    def _set_shared_data(self, key: str, data: Any) -> Dict[str, Any]:
        """공유 데이터 설정"""
        timestamp = datetime.now().isoformat()

        self.shared_data[key] = {
            "data": data,
            "timestamp": timestamp,
            "access_count": 0,
        }

        return {
            "status": "success",
            "key": key,
            "timestamp": timestamp,
            "data_size": len(str(data)) if isinstance(data, (str, dict, list)) else 1,
        }

    def _get_shared_data(self, key: str) -> Dict[str, Any]:
        """공유 데이터 조회"""
        if key not in self.shared_data:
            return {
                "status": "not_found",
                "key": key,
                "message": "Shared data not found",
            }

        # 접근 카운트 증가
        self.shared_data[key]["access_count"] += 1

        return {
            "status": "success",
            "key": key,
            "data": self.shared_data[key]["data"],
            "timestamp": self.shared_data[key]["timestamp"],
            "access_count": self.shared_data[key]["access_count"],
        }

    def _register_dependency(
        self, agent_id: str, depends_on: List[str]
    ) -> Dict[str, Any]:
        """Agent 간 의존성 등록"""
        self.dependencies[agent_id] = {
            "depends_on": depends_on,
            "registered_at": datetime.now().isoformat(),
            "resolved": False,
        }

        return {
            "status": "success",
            "agent_id": agent_id,
            "dependencies": depends_on,
            "dependency_count": len(depends_on),
        }

    def _check_dependencies(
        self, agent_id: str, depends_on: List[str]
    ) -> Dict[str, Any]:
        """의존성 확인"""
        if not depends_on:
            return {
                "status": "success",
                "agent_id": agent_id,
                "can_execute": True,
                "dependencies_resolved": True,
                "pending_dependencies": [],
            }

        pending_dependencies = []

        for dep_agent_id in depends_on:
            if dep_agent_id not in self.agent_states:
                pending_dependencies.append(
                    {"agent_id": dep_agent_id, "reason": "Agent not started"}
                )
            else:
                current_status = self.agent_states[dep_agent_id].get(
                    "current_status", "unknown"
                )
                if current_status not in ["completed", "success"]:
                    pending_dependencies.append(
                        {
                            "agent_id": dep_agent_id,
                            "reason": f"Status: {current_status}",
                        }
                    )

        can_execute = len(pending_dependencies) == 0

        # 의존성 해결 상태 업데이트
        if agent_id in self.dependencies:
            self.dependencies[agent_id]["resolved"] = can_execute
            self.dependencies[agent_id]["last_checked"] = datetime.now().isoformat()

        return {
            "status": "success",
            "agent_id": agent_id,
            "can_execute": can_execute,
            "dependencies_resolved": can_execute,
            "pending_dependencies": pending_dependencies,
            "total_dependencies": len(depends_on),
        }

    def _complete_execution(
        self, agent_id: str, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Agent 실행 완료 처리"""
        completion_time = datetime.now().isoformat()

        # 실행 순서 기록
        self.execution_order.append(
            {
                "agent_id": agent_id,
                "completed_at": completion_time,
                "result_summary": {
                    "status": result.get("status", "unknown"),
                    "has_error": "error" in result,
                    "data_keys": (
                        list(result.keys()) if isinstance(result, dict) else []
                    ),
                },
            }
        )

        # Agent 상태를 완료로 업데이트
        if agent_id in self.agent_states:
            completion_state = {
                "timestamp": completion_time,
                "status": "completed",
                "step_index": -1,  # 완료 표시
                "current_action": "execution_completed",
                "data": result,
                "progress": 1.0,
            }

            self.agent_states[agent_id]["states"].append(completion_state)
            self.agent_states[agent_id]["current_status"] = "completed"
            self.agent_states[agent_id]["completed_at"] = completion_time

        return {
            "status": "success",
            "agent_id": agent_id,
            "completed_at": completion_time,
            "execution_order": len(self.execution_order),
            "dependent_agents_notified": self._notify_dependent_agents(agent_id),
        }

    def _notify_dependent_agents(self, completed_agent_id: str) -> List[str]:
        """완료된 Agent에 의존하는 다른 Agent들에게 알림"""
        notified_agents = []

        for agent_id, dep_info in self.dependencies.items():
            if completed_agent_id in dep_info.get("depends_on", []):
                # 의존성 다시 확인
                dep_check = self._check_dependencies(agent_id, dep_info["depends_on"])
                if dep_check.get("can_execute", False):
                    notified_agents.append(agent_id)

        return notified_agents

    def get_execution_status(self) -> Dict[str, Any]:
        """전체 실행 상태 조회"""
        active_agents = []
        completed_agents = []
        failed_agents = []

        for agent_id, state_info in self.agent_states.items():
            current_status = state_info.get("current_status", "unknown")
            if current_status == "completed":
                completed_agents.append(agent_id)
            elif current_status in ["error", "failed"]:
                failed_agents.append(agent_id)
            else:
                active_agents.append(agent_id)

        return {
            "total_agents": len(self.agent_states),
            "active_agents": active_agents,
            "completed_agents": completed_agents,
            "failed_agents": failed_agents,
            "execution_order": self.execution_order,
            "shared_data_keys": list(self.shared_data.keys()),
            "dependency_count": len(self.dependencies),
        }

    def clear_all_states(self):
        """모든 상태 초기화"""
        self.agent_states = {}
        self.shared_data = {}
        self.dependencies = {}
        self.execution_order = []

    def export_state_snapshot(self) -> Dict[str, Any]:
        """현재 상태 스냅샷 내보내기"""
        return {
            "timestamp": datetime.now().isoformat(),
            "agent_states": self.agent_states,
            "shared_data": {k: v for k, v in self.shared_data.items()},  # 복사본
            "dependencies": self.dependencies,
            "execution_order": self.execution_order,
            "execution_status": self.get_execution_status(),
        }
