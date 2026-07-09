from __future__ import annotations

from maios.autonomous import MAIOSAgent


def main() -> None:
    agent = MAIOSAgent(max_workers=2)
    missions = [
        agent.submit_goal("Prepare an autonomous MAIOS status brief."),
        agent.submit_goal("Summarize the current MAIOS operating loop."),
    ]

    agent.start_background()
    agent.wait_until_idle()
    agent.stop_background()

    for mission in missions:
        record = agent.scheduler.get(mission.mission_id)
        print(f"{record.mission_id}: {record.status}")
        if record.result:
            print(record.result.final_output)


if __name__ == "__main__":
    main()
