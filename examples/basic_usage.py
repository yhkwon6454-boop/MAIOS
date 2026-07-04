from __future__ import annotations

import maios


def main() -> None:
    result = maios.run("Summarize the current MAIOS runtime status.")
    print(result.status.value)
    print(result.final_output)


if __name__ == "__main__":
    main()
