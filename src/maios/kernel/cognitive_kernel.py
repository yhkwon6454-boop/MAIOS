from maios.runtime.models import CognitivePacket, CognitiveProcess, Mission
from maios.runtime.plan import Plan


class CognitiveKernel:

    def execute(self, plan: Plan):

        return {
            "objective": plan.objective,
            "analysis": f"Mission Analysis Complete: {plan.objective}",
            "tasks": plan.tasks,
            "risk": plan.risk,
            "priority": plan.priority,
            "status": "THINK_COMPLETE",
        }

    def validate(self, result):

        return result["status"] == "THINK_COMPLETE"

    def build_processes(self, mission: Mission) -> list[CognitiveProcess]:
        return [
            CognitiveProcess(mission.mission_id, "Mission Understanding", "ANALYSIS"),
            CognitiveProcess(mission.mission_id, "Response Development", "SYNTHESIS"),
            CognitiveProcess(mission.mission_id, "Final Answer", "WRITING"),
        ]

    def build_packets(
        self,
        mission: Mission,
        processes: list[CognitiveProcess],
    ) -> list[CognitivePacket]:
        instructions = [
            f"{mission.title}: analyze the mission objective and constraints.",
            f"{mission.title}: develop an actionable response for the mission.",
            f"{mission.title}: produce the final output as {mission.expected_output}.",
        ]
        strategies = [
            ["Mission Analysis"],
            ["Synthesis"],
            ["Clarity First"],
        ]
        memory = [
            ["mission", "context"],
            ["mission", "context"],
            ["style_guide", "context"],
        ]

        return [
            CognitivePacket(
                process_id=process.process_id,
                instruction=instructions[index],
                strategy=strategies[index],
                required_memory=memory[index],
                output_format=mission.expected_output,
            )
            for index, process in enumerate(processes)
        ]
