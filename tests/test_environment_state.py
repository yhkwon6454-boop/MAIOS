from __future__ import annotations

from maios.kernel import EnvironmentState, UserModel


def test_environment_state_normalizes_and_updates_values():
    state = EnvironmentState(
        signals={"tempo": "fast"},
        constraints=["low-latency"],
        resources={"cpu": 0.8},
        risk_level="high",
    )

    state.update(
        signals={"weather": "clear"},
        constraints=("low-latency", "secure"),
        resources={"memory": 0.6},
        risk_level="critical",
    )

    assert state.risk_level == "CRITICAL"
    assert state.signals["tempo"] == "fast"
    assert state.signals["weather"] == "clear"
    assert state.constraints == ("low-latency", "secure")
    assert state.resources["memory"] == 0.6
    assert state.to_dict()["constraints"] == ["low-latency", "secure"]


def test_user_model_tracks_preferences_and_intent_history():
    user = UserModel(trust_level=2.0)

    user.update_preferences({"detail": "concise"})
    user.observe_intent("Plan next mission")
    user.observe_intent("   ")

    assert user.trust_level == 1.0
    assert user.preferences["detail"] == "concise"
    assert user.intent_history == ["Plan next mission"]
