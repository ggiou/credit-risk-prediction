"""프롬프트 버전 동기화 계약 테스트.

FastAPI는 요청의 promptVersion이 서버 설정과 다르면 422를 낸다. 따라서
ai-server와 Spring의 값이 어긋나면 배포 직후 모든 예측이 실패한다.

코드 기본값만 맞추는 것으로는 부족하다. docker-compose가 두 서비스에
AI_PROMPT_VERSION을 명시적으로 주입하므로, compose 기본값이 낡아 있으면
코드 기본값은 런타임에 그대로 덮여 상향이 무력화된다.
그래서 코드·설정·배포 예시 여덟 곳을 한 번에 고정한다.
"""

import re
from pathlib import Path

import pytest

from app.config import Settings
from app.schemas import PredictRequest


REPO_ROOT = Path(__file__).resolve().parents[2]
SPRING_APPLICATION_YML = REPO_ROOT / "spring-app" / "src" / "main" / "resources" / "application.yml"
SPRING_SECRET_EXAMPLE = REPO_ROOT / "config" / "application-secret.example.yml"
ROOT_ENV_EXAMPLE = REPO_ROOT / ".env.example"
AI_SERVER_ENV_EXAMPLE = REPO_ROOT / "ai-server" / ".env.example"
DOCKER_COMPOSE = REPO_ROOT / "docker-compose.yml"


def _expected(monkeypatch: pytest.MonkeyPatch) -> str:
    """환경변수를 걷어낸 ai-server 기본값이 단일 기준이다."""

    monkeypatch.delenv("AI_PROMPT_VERSION", raising=False)
    return Settings.from_env().prompt_version


# --- 코드 기본값 --------------------------------------------------------


def test_schema_default_matches_settings_default(monkeypatch):
    assert PredictRequest.model_fields["promptVersion"].default == _expected(monkeypatch)


# --- Spring 설정 --------------------------------------------------------


def test_spring_application_yml_matches(monkeypatch):
    text = SPRING_APPLICATION_YML.read_text(encoding="utf-8")
    match = re.search(r"prompt-version:\s*\$\{AI_PROMPT_VERSION:([^}]+)\}", text)
    assert match, "application.yml에서 prompt-version 기본값을 찾지 못했다"
    assert match.group(1).strip() == _expected(monkeypatch)


def test_spring_secret_example_matches(monkeypatch):
    text = SPRING_SECRET_EXAMPLE.read_text(encoding="utf-8")
    match = re.search(r'prompt-version:\s*"([^"]+)"', text)
    assert match, "application-secret.example.yml에서 prompt-version을 찾지 못했다"
    assert match.group(1).strip() == _expected(monkeypatch)


# --- 배포/실행 예시 -----------------------------------------------------


@pytest.mark.parametrize(
    "path_name",
    ["ROOT_ENV_EXAMPLE", "AI_SERVER_ENV_EXAMPLE"],
)
def test_env_examples_match(monkeypatch, path_name):
    path = {"ROOT_ENV_EXAMPLE": ROOT_ENV_EXAMPLE, "AI_SERVER_ENV_EXAMPLE": AI_SERVER_ENV_EXAMPLE}[path_name]
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^AI_PROMPT_VERSION=(.+)$", text, re.MULTILINE)
    assert match, f"{path.name}에서 AI_PROMPT_VERSION을 찾지 못했다"
    assert match.group(1).strip() == _expected(monkeypatch)


def test_docker_compose_defaults_match(monkeypatch):
    """compose는 ai-server와 spring-app 두 서비스에 같은 값을 주입해야 한다."""

    text = DOCKER_COMPOSE.read_text(encoding="utf-8")
    matches = re.findall(r"AI_PROMPT_VERSION:\s*\$\{AI_PROMPT_VERSION:-([^}]+)\}", text)
    assert len(matches) == 2, f"docker-compose.yml의 AI_PROMPT_VERSION 기본값이 2곳이어야 한다: {matches}"
    expected = _expected(monkeypatch)
    for value in matches:
        assert value.strip() == expected


def test_docker_compose_defaults_are_identical():
    """두 서비스 기본값이 서로 달라지면 배포 즉시 422가 난다."""

    text = DOCKER_COMPOSE.read_text(encoding="utf-8")
    matches = {value.strip() for value in re.findall(
        r"AI_PROMPT_VERSION:\s*\$\{AI_PROMPT_VERSION:-([^}]+)\}", text
    )}
    assert len(matches) == 1, f"서비스별 프롬프트 버전 기본값이 어긋난다: {matches}"


# --- 전 지점 일괄 확인 --------------------------------------------------


def test_no_stale_version_remains(monkeypatch):
    """동기화 지점 어디에도 기준값이 아닌 프롬프트 버전이 남지 않아야 한다."""

    expected = _expected(monkeypatch)
    sources = [
        SPRING_APPLICATION_YML,
        SPRING_SECRET_EXAMPLE,
        ROOT_ENV_EXAMPLE,
        AI_SERVER_ENV_EXAMPLE,
        DOCKER_COMPOSE,
    ]
    stale: list[str] = []
    for path in sources:
        for raw in re.findall(
            r"(?:AI_PROMPT_VERSION[=:]\s*(?:\$\{AI_PROMPT_VERSION:-)?|prompt-version:\s*\"?(?:\$\{AI_PROMPT_VERSION:)?)"
            r"([v][0-9]+\.[0-9]+)",
            path.read_text(encoding="utf-8"),
        ):
            if raw != expected:
                stale.append(f"{path.name}: {raw}")
    assert not stale, f"기준값 {expected}과 다른 버전이 남아 있다: {stale}"


# --- 환경변수 우선순위 --------------------------------------------------


def test_env_override_still_wins(monkeypatch):
    monkeypatch.setenv("AI_PROMPT_VERSION", "v9.9")
    assert Settings.from_env().prompt_version == "v9.9"
