from __future__ import annotations

import maios


def main() -> None:
    result = maios.run("Prepare a concise MAIOS demo mission brief.")
    print(result.final_output)
    print(f"\nStatus: {result.status.value}")
    print(f"Knowledge records: {result.knowledge_count}")


if __name__ == "__main__":
    main()
