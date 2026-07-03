from __future__ import annotations

from maios.kernel.cognitive_kernel import CognitiveKernel
from maios.runtime.models import CognitivePacket, CognitiveProcess, Mission, MissionType
from maios.runtime.tree import CognitiveProcessTree, ProcessNode


class MissionScheduler:
    """
    Mission을 Cognitive Process Tree로 분해하는 스케줄러.

    v4.2-alpha에서는 규칙 기반 분해를 사용한다.
    향후 LLM 기반 동적 분해, 병렬 스케줄링, 의존성 그래프로 확장한다.
    """

    def __init__(self) -> None:
        self.cognitive_kernel = CognitiveKernel()

    def schedule(self, mission: Mission) -> CognitiveProcessTree:
        if mission.mission_type == MissionType.MILITARY_RESEARCH:
            return self._schedule_military_research(mission)

        if mission.mission_type == MissionType.WRITING:
            return self._schedule_writing(mission)

        if mission.mission_type == MissionType.TRANSLATION:
            return self._schedule_translation(mission)

        return self._schedule_general(mission)

    def _packet(
        self,
        process: CognitiveProcess,
        instruction: str,
        strategy: list[str],
        memory: list[str],
        output_format: str,
    ) -> CognitivePacket:
        return CognitivePacket(
            process_id=process.process_id,
            instruction=instruction,
            strategy=strategy,
            required_memory=memory,
            output_format=output_format,
        )

    def _schedule_military_research(self, mission: Mission) -> CognitiveProcessTree:
        p1 = CognitiveProcess(mission.mission_id, "Threat Research", "RESEARCH")
        p2 = CognitiveProcess(mission.mission_id, "Operational Impact Analysis", "ANALYSIS", [p1.process_id])
        p3 = CognitiveProcess(mission.mission_id, "Response Option Development", "STRATEGY", [p2.process_id])
        p4 = CognitiveProcess(mission.mission_id, "Final Military Brief", "WRITING", [p3.process_id])

        n1 = ProcessNode(
            p1,
            packets=[
                self._packet(
                    p1,
                    f"{mission.title}: 위협의 구성요소, 능력, 제한사항을 조사하라.",
                    ["OODA", "Systems Thinking"],
                    ["military", "doctrine"],
                    "research_note",
                )
            ],
        )
        n2 = ProcessNode(
            p2,
            packets=[
                self._packet(
                    p2,
                    f"{mission.title}: 작전적 영향과 취약점을 분석하라.",
                    ["Red Team", "COA Analysis"],
                    ["military", "strategy"],
                    "analysis_brief",
                )
            ],
        )
        n3 = ProcessNode(
            p3,
            packets=[
                self._packet(
                    p3,
                    f"{mission.title}: 대응방안을 단기·중기·장기로 제시하라.",
                    ["Scenario Planning", "Risk Analysis"],
                    ["strategy", "doctrine"],
                    "options",
                )
            ],
        )
        n4 = ProcessNode(
            p4,
            packets=[
                self._packet(
                    p4,
                    f"{mission.title}: 지휘관 보고용 최종 요약을 작성하라.",
                    ["Executive Briefing", "Clarity First"],
                    ["style_guide"],
                    mission.expected_output,
                )
            ],
        )

        n1.children.append(n2)
        n2.children.append(n3)
        n3.children.append(n4)
        return CognitiveProcessTree(mission=mission, root_nodes=[n1])

    def _schedule_writing(self, mission: Mission) -> CognitiveProcessTree:
        p1 = CognitiveProcess(mission.mission_id, "Outline", "PLANNING")
        p2 = CognitiveProcess(mission.mission_id, "Draft", "WRITING", [p1.process_id])
        p3 = CognitiveProcess(mission.mission_id, "Revision", "QA", [p2.process_id])

        n1 = ProcessNode(
            p1,
            [self._packet(p1, f"{mission.title}: 독자와 목적에 맞는 목차를 설계하라.", ["Reader-Centered Structure"], ["project", "style_guide"], "outline")]
        )
        n2 = ProcessNode(
            p2,
            [self._packet(p2, f"{mission.title}: 목차에 따라 본문 초안을 작성하라.", ["Logical Flow"], ["project", "style_guide"], mission.expected_output)]
        )
        n3 = ProcessNode(
            p3,
            [self._packet(p3, f"{mission.title}: 가독성, 구조, 완성도를 검수하라.", ["Quality Review"], ["style_guide"], "revision_note")]
        )
        n1.children.append(n2)
        n2.children.append(n3)
        return CognitiveProcessTree(mission=mission, root_nodes=[n1])

    def _schedule_translation(self, mission: Mission) -> CognitiveProcessTree:
        p1 = CognitiveProcess(mission.mission_id, "Terminology Pass", "RESEARCH")
        p2 = CognitiveProcess(mission.mission_id, "Translation Pass", "TRANSLATION", [p1.process_id])
        p3 = CognitiveProcess(mission.mission_id, "Review Pass", "QA", [p2.process_id])

        n1 = ProcessNode(
            p1,
            [self._packet(p1, f"{mission.title}: 핵심 용어와 번역 원칙을 정리하라.", ["Terminology Consistency"], ["terminology"], "term_note")]
        )
        n2 = ProcessNode(
            p2,
            [self._packet(p2, f"{mission.title}: 의미 보존 원칙에 따라 번역하라.", ["Meaning Preservation"], ["terminology", "style_guide"], mission.expected_output)]
        )
        n3 = ProcessNode(
            p3,
            [self._packet(p3, f"{mission.title}: 누락, 오역, 문체를 검수하라.", ["Translation QA"], ["terminology", "style_guide"], "qa_note")]
        )
        n1.children.append(n2)
        n2.children.append(n3)
        return CognitiveProcessTree(mission=mission, root_nodes=[n1])

    def _schedule_general(self, mission: Mission) -> CognitiveProcessTree:
        processes = self.cognitive_kernel.build_processes(mission)
        packets = self.cognitive_kernel.build_packets(mission, processes)
        nodes = [ProcessNode(process=p, packets=[packet]) for p, packet in zip(processes, packets)]

        for i in range(len(nodes) - 1):
            nodes[i].children.append(nodes[i + 1])

        return CognitiveProcessTree(mission=mission, root_nodes=nodes[:1])
