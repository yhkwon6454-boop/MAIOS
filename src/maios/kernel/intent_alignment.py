from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from maios.knowledge.ontology import OntologyAdapter


def _terms(text: str) -> set[str]:
    lowered = text.lower()
    terms = {token for token in re.findall(r"[a-zA-Z0-9_]+", lowered) if len(token) > 2}
    for run in re.findall(r"[가-힣]{2,}", lowered):
        terms.update(run[index : index + 2] for index in range(len(run) - 1))
    return terms


@dataclass(frozen=True)
class CommandersIntent:
    """Commander's intent: purpose, end state, key tasks, and the limits."""

    purpose: str = ""
    end_state: str = ""
    key_tasks: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    acceptable_risks: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommandersIntent:
        return cls(
            purpose=str(data.get("purpose", "")),
            end_state=str(data.get("end_state", "")),
            key_tasks=tuple(data.get("key_tasks", ())),
            constraints=tuple(data.get("constraints", ())),
            acceptable_risks=tuple(data.get("acceptable_risks", ())),
        )

    @classmethod
    def load(cls, path: str | Path) -> CommandersIntent:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "purpose": self.purpose,
            "end_state": self.end_state,
            "key_tasks": list(self.key_tasks),
            "constraints": list(self.constraints),
            "acceptable_risks": list(self.acceptable_risks),
        }


@dataclass(frozen=True)
class AlignmentReport:
    verdict: str  # ALIGNED | CHECK | CONFLICT
    supported_tasks: tuple[str, ...] = ()
    purpose_link: bool = False
    touched_constraints: tuple[str, ...] = ()
    covered_by_risks: tuple[str, ...] = ()
    rationale: str = ""
    expanded_terms: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "supported_tasks": list(self.supported_tasks),
            "purpose_link": self.purpose_link,
            "touched_constraints": list(self.touched_constraints),
            "covered_by_risks": list(self.covered_by_risks),
            "rationale": self.rationale,
            "expanded_terms": list(self.expanded_terms),
        }


class IntentAlignmentChecker:
    """Judges whether an action aligns with the commander's intent.

    Surface-term matching (Hangul bigrams + words), optionally widened by an
    ontology so conceptually related actions count. This is a heuristic
    triage - ALIGNED/CHECK/CONFLICT - not a semantic proof; CHECK means a
    human should look.
    """

    def __init__(
        self,
        intent: CommandersIntent,
        ontology: OntologyAdapter | None = None,
        threshold: float = 0.3,
    ) -> None:
        self.intent = intent
        self.ontology = ontology
        self.threshold = min(1.0, max(0.05, threshold))

    def check(self, action: str) -> AlignmentReport:
        expanded: tuple[str, ...] = ()
        action_text = action
        if self.ontology is not None and self.ontology.available:
            expanded = self.ontology.expand_query(action)
            if expanded:
                action_text = action + " " + " ".join(expanded)
        action_terms = _terms(action_text)

        supported = tuple(
            task for task in self.intent.key_tasks if self._matches(action_terms, task)
        )
        purpose_link = bool(
            (self.intent.purpose and self._matches(action_terms, self.intent.purpose))
            or (self.intent.end_state and self._matches(action_terms, self.intent.end_state))
        )
        touched = tuple(
            constraint
            for constraint in self.intent.constraints
            if self._matches(action_terms, constraint)
        )
        covered = tuple(
            risk for risk in self.intent.acceptable_risks if self._matches(action_terms, risk)
        )

        if touched and not covered:
            verdict = "CONFLICT"
            rationale = f"제한사항과 충돌: {', '.join(touched)}"
        elif supported or purpose_link:
            verdict = "ALIGNED"
            parts = []
            if supported:
                parts.append(f"핵심과업 지원: {', '.join(supported)}")
            if purpose_link:
                parts.append("목적·최종상태와 연결")
            if touched and covered:
                parts.append(f"제한 접촉이나 수용위험 범위 내: {', '.join(covered)}")
            rationale = "; ".join(parts)
        else:
            verdict = "CHECK"
            rationale = "의도 요소와의 연결이 확인되지 않음 - 인간 확인 필요"

        return AlignmentReport(
            verdict=verdict,
            supported_tasks=supported,
            purpose_link=purpose_link,
            touched_constraints=touched,
            covered_by_risks=covered,
            rationale=rationale,
            expanded_terms=expanded,
        )

    def _matches(self, action_terms: set[str], element: str) -> bool:
        element_terms = _terms(element)
        if not element_terms:
            return False
        overlap = len(action_terms & element_terms) / len(element_terms)
        return overlap >= self.threshold
