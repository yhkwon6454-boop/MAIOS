from __future__ import annotations

from maios.runtime.models import CognitivePacket, CognitiveProcess, Mission, MissionType


class CognitiveKernel:
    """
    Mission을 Cognitive Process Tree와 Cognitive Packet으로 분해한다.
    """

    def build_processes(self, mission: Mission) -> list[CognitiveProcess]:
        if mission.mission_type == MissionType.MILITARY_RESEARCH:
            names = [
                ("Threat Environment Review", "RESEARCH"),
                ("Operational Implication Analysis", "ANALYSIS"),
                ("Response Option Development", "STRATEGY"),
                ("Final Report Composition", "WRITING"),
            ]
        elif mission.mission_type == MissionType.TRANSLATION:
            names = [
                ("Terminology Review", "RESEARCH"),
                ("Translation Draft", "TRANSLATION"),
                ("Style and Accuracy Review", "QA"),
            ]
        elif mission.mission_type == MissionType.WRITING:
            names = [
                ("Outline Design", "PLANNING"),
                ("Draft Composition", "WRITING"),
                ("Revision and Polish", "QA"),
            ]
        else:
            names = [
                ("Problem Structuring", "ANALYSIS"),
                ("Draft Response", "WRITING"),
                ("Quality Review", "QA"),
            ]

        return [
            CognitiveProcess(
                mission_id=mission.mission_id,
                name=name,
                process_type=process_type,
            )
            for name, process_type in names
        ]

    def build_packets(self, mission: Mission, processes: list[CognitiveProcess]) -> list[CognitivePacket]:
        packets: list[CognitivePacket] = []

        for process in processes:
            strategy = self._select_strategy(mission, process)
            memory = self._select_memory(mission, process)

            packets.append(
                CognitivePacket(
                    process_id=process.process_id,
                    instruction=f"{mission.title}: {process.name} 수행. 목적: {mission.objective}",
                    strategy=strategy,
                    required_memory=memory,
                    output_format=mission.expected_output,
                )
            )

        return packets

    def _select_strategy(self, mission: Mission, process: CognitiveProcess) -> list[str]:
        if mission.mission_type == MissionType.MILITARY_RESEARCH:
            return ["OODA", "Systems Thinking", "Red Team"]
        if mission.mission_type == MissionType.STRATEGY_ANALYSIS:
            return ["COA Analysis", "Red Team", "Scenario Planning"]
        if mission.mission_type == MissionType.TRANSLATION:
            return ["Meaning Preservation", "Terminology Consistency"]
        if mission.mission_type == MissionType.WRITING:
            return ["Reader-Centered Structure", "Logical Flow"]
        return ["Problem Structuring", "Clarity First"]

    def _select_memory(self, mission: Mission, process: CognitiveProcess) -> list[str]:
        if mission.mission_type == MissionType.MILITARY_RESEARCH:
            return ["military", "strategy", "doctrine"]
        if mission.mission_type == MissionType.TRANSLATION:
            return ["terminology", "style_guide"]
        if mission.mission_type == MissionType.WRITING:
            return ["project", "reader_profile", "style_guide"]
        return ["general"]
