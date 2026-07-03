from __future__ import annotations


class InMemoryKnowledgeStore:
    """
    v4.0-alpha용 단순 메모리 저장소.
    향후 파일 기반 KFS, 벡터 DB, 지식 그래프로 확장한다.
    """

    def __init__(self) -> None:
        self.data: dict[str, str] = {
            "military": "군사 연구는 위협, 작전환경, 대응방안, 위험을 구조적으로 다룬다.",
            "strategy": "전략 분석은 목적, 수단, 방법, 위험, 실행가능성을 함께 평가한다.",
            "doctrine": "교리 분석은 원칙, 임무, 전력, 지휘통제, 전장기능을 기준으로 한다.",
            "terminology": "번역은 용어 일관성과 의미 보존을 우선한다.",
            "style_guide": "문체는 명확성, 전문성, 재사용성을 우선한다.",
            "project": "장기 프로젝트는 목표, 산출물, 버전, 변경 이력을 관리한다.",
        }

    def retrieve(self, keys: list[str]) -> dict[str, str]:
        return {key: self.data[key] for key in keys if key in self.data}

    def store(self, key: str, value: str) -> None:
        self.data[key] = value
