import pytest

from app.config import Settings


def test_prompt_cache_settings_use_ai_prompt_version(monkeypatch):
    monkeypatch.setenv("AI_PROMPT_VERSION", "v3.6")
    monkeypatch.setenv("OPENAI_PROMPT_CACHE_ENABLED", "true")
    monkeypatch.setenv("OPENAI_PROMPT_CACHE_MODE", "explicit")
    monkeypatch.setenv("OPENAI_PROMPT_CACHE_TTL", "30m")
    monkeypatch.setenv("OPENAI_PROMPT_CACHE_KEY_PREFIX", "miribom-risk-explanation")

    settings = Settings.from_env()

    assert settings.prompt_version == "v3.6"
    assert settings.openai_prompt_cache_enabled is True
    assert settings.openai_prompt_cache_mode == "explicit"
    assert settings.openai_prompt_cache_ttl == "30m"
    assert settings.openai_prompt_cache_key_prefix == "miribom-risk-explanation"
    assert not hasattr(settings, "openai_prompt_version")


def test_prompt_cache_can_be_disabled(monkeypatch):
    monkeypatch.setenv("OPENAI_PROMPT_CACHE_ENABLED", "false")

    assert Settings.from_env().openai_prompt_cache_enabled is False


def test_prompt_cache_rejects_unsupported_ttl(monkeypatch):
    monkeypatch.setenv("OPENAI_PROMPT_CACHE_TTL", "24h")

    with pytest.raises(ValueError, match="OPENAI_PROMPT_CACHE_TTL must be '30m'"):
        Settings.from_env()
