from maios.config import MAIOSConfig, load_config


def _ensure_unset(monkeypatch, *names: str) -> None:
    """Unset env vars while registering restoration even for absent ones.

    ``monkeypatch.delenv(raising=False)`` records nothing for absent vars, so
    values injected later by ``load_dotenv`` would leak into other tests.
    """
    for name in names:
        monkeypatch.setenv(name, "sentinel")
        monkeypatch.delenv(name)


def test_config_create():
    config = MAIOSConfig()
    assert config is not None


def test_load_config_reads_env_file(tmp_path, monkeypatch):
    _ensure_unset(monkeypatch, "MAIOS_MODEL_PROVIDER", "ANTHROPIC_API_KEY")
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MAIOS_MODEL_PROVIDER=claude\nANTHROPIC_API_KEY=test-key\n",
        encoding="utf-8",
    )

    config = load_config(env_file)

    assert config.model_provider == "claude"
    assert config.claude_api_key == "test-key"


def test_load_config_process_environment_wins_over_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("MAIOS_MODEL_PROVIDER", "openai")
    env_file = tmp_path / ".env"
    env_file.write_text("MAIOS_MODEL_PROVIDER=claude\n", encoding="utf-8")

    config = load_config(env_file)

    assert config.model_provider == "openai"


def test_load_config_without_env_file_uses_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _ensure_unset(monkeypatch, "MAIOS_MODEL_PROVIDER", "MAIOS_MODEL")

    config = load_config()

    assert config.model_provider == "mock"
