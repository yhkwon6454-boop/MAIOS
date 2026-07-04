from dataclasses import dataclass, field


@dataclass
class Plan:
    """
    Mission Planner가 생성하는 실행 계획
    """

    objective: str
    tasks: list[str] = field(default_factory=list)
    risk: str = "MEDIUM"
    priority: str = "NORMAL"
    output: str = ""

    def summary(self) -> dict:
        return {
            "objective": self.objective,
            "tasks": self.tasks,
            "risk": self.risk,
            "priority": self.priority,
            "output": self.output,
        }
