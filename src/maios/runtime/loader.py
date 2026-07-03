from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from maios.runtime.models import Mission


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """
    최소 의존성 구현을 위한 아주 단순한 YAML 파서.
    중첩 구조가 필요한 경우 PyYAML 사용을 권장한다.
    """
    result: dict[str, Any] = {}
    current_list_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue

        if line.startswith("  - ") and current_list_key:
            result.setdefault(current_list_key, []).append(line[4:].strip().strip('"'))
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"')

            if value == "":
                result[key] = []
                current_list_key = key
            else:
                result[key] = value
                current_list_key = None

    return result


def load_mission(path: str | Path) -> Mission:
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = _parse_simple_yaml(text)

    return Mission.from_dict(data)
