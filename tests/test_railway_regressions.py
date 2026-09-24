"""Regression coverage for deployed chat, uploads, health probes and shutdown."""
import json
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_bounded(action):
    result, errors = [], []

    def run():
        try:
            result.append(action())
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout=2)
    assert not thread.is_alive(), "Optimizer deadlocked"
    if errors:
        raise errors[0]
    return result[0]


@pytest.fixture
def optimizer(monkeypatch, tmp_path):
    from services import self_optimizer as module
    monkeypatch.setattr(module, "LEARNING_DB_PATH", tmp_path / "learning.json")
    monkeypatch.setattr(module, "KNOWLEDGE_GRAPH_PATH", tmp_path / "graph.json")
    return module.AdvancedOptimizer()


def test_optimizer_report_does_not_deadlock(optimizer):
    report = run_bounded(optimizer.get_session_report)
    assert report["top_provider"] == "auto"
    assert report["learning_events"] == 0


def test_optimizer_autosave_does_not_freeze_chat(optimizer, tmp_path):
    from services.self_optimizer import BACKUP_INTERVAL

    def learn():
        for _ in range(BACKUP_INTERVAL):
            optimizer.learn_from_interaction("q", "a", "physics", "test", True, 0.1)
        return optimizer.get_session_report()

    report = run_bounded(learn)
    saved = json.loads((tmp_path / "learning.json").read_text())
    assert saved["subject_expertise"]["physics"]["attempts"] == BACKUP_INTERVAL
    assert report["learning_events"] == BACKUP_INTERVAL


@pytest.mark.parametrize("answer", ["4", "Yes", "No", "0", "سلام"])
def test_valid_short_model_answers_are_returned(monkeypatch, answer):
    from services import llm, colab_worker
    monkeypatch.setattr(colab_worker, "is_live", lambda: False)
    monkeypatch.setattr(llm, "_build_provider_chain", lambda *a: [("test", lambda *a: answer)])
    assert llm.ask_ai("What is two plus two? Answer with one number.") == answer


@pytest.mark.parametrize("bad", [None, "", "  ", "[Error: unavailable]"])
def test_empty_or_error_model_responses_still_fall_back(monkeypatch, bad):
    from services import llm, colab_worker
    monkeypatch.setattr(colab_worker, "is_live", lambda: False)
    monkeypatch.setattr(llm, "_build_provider_chain", lambda *a: [
        ("first", lambda *a: bad), ("second", lambda *a: "4")
    ])
    assert llm.ask_ai("What is two plus two? Answer with one number.") == "4"


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as test_client:
        yield test_client


def test_railway_and_docker_probes_are_allowed(client):
    for host in ("healthcheck.railway.app", "127.0.0.1"):
        response = client.get("/health", headers={"host": host})
        assert response.status_code == 200, response.text
    assert client.get("/health", headers={"host": "untrusted.example"}).status_code == 400


def test_ui_version_matches_running_release(client):
    response = client.get("/api/version")
    assert response.status_code == 200
    assert response.json()["version"] == (ROOT / "VERSION").read_text().strip()
    assert response.headers["cache-control"] == "no-store"


def test_uploaded_text_reaches_model_context(client, monkeypatch, tmp_path):
    from routes import chat
    from services import quota, usage_tracker
    captured = []

    def answer(question, context, *args):
        captured.append(context)
        return "The document contains the code PRISM472."

    monkeypatch.setattr(chat, "ask_ai", answer)
    monkeypatch.setattr(chat, "auto_search_context", lambda *a: "")
    monkeypatch.setattr(chat, "is_search_needed", lambda *a: False)
    monkeypatch.setattr(chat.rag_cache, "_root", tmp_path / "rag")
    monkeypatch.setattr(quota, "LEDGER", tmp_path / "quota.json")
    monkeypatch.setattr(usage_tracker, "_DATA", tmp_path / "usage.json")
    response = client.post("/chat/send", data={
        "message": "Extract the code from this file.", "generate_images": "false"
    }, files={"files": ("note.txt", b"Code: PRISM472", "text/plain")})
    assert response.status_code == 200, response.text
    assert captured and "Code: PRISM472" in captured[0]
    assert response.json()["rag_files_loaded"] == 1


def test_password_login_returns_usable_token(client, monkeypatch, tmp_path):
    from routes import login
    monkeypatch.setattr(login, "user_db", login.UserDatabase(tmp_path / "users.json"))
    registration = client.post("/auth/register", json={
        "username": "railway_test", "email": "railway_test@example.com",
        "password": "local-test-password-813", "full_name": "Test User"
    })
    assert registration.status_code == 201, registration.text
    response = client.post("/auth/login", data={
        "username": "railway_test", "password": "local-test-password-813"
    })
    assert response.status_code == 200
    me = client.get("/auth/me", headers={"Authorization": "Bearer " + response.json()["access_token"]})
    assert me.status_code == 200
    assert me.json()["username"] == "railway_test"


def test_lifespan_stops_background_agent():
    from fastapi.testclient import TestClient
    from main import app
    from services.agent_orchestrator import agent_orchestrator
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert agent_orchestrator.get_status()["agent"] == "running"
    assert agent_orchestrator.get_status()["agent"] == "stopped"


def test_docker_dependency_failure_fails_build(tmp_path):
    """Execute the actual Docker RUN command with an intentionally failing pip."""
    import os
    dockerfile = (ROOT / "Dockerfile").read_text()
    command = next(line[4:] for line in dockerfile.replace("\\\n", " ").splitlines()
                   if line.startswith("RUN pip install"))
    pip = tmp_path / "pip"
    pip.write_text("#!/bin/sh\nexit 7\n")
    pip.chmod(0o755)
    result = subprocess.run(["sh", "-c", command], env={
        **os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"]
    }, capture_output=True, timeout=5)
    assert result.returncode == 7, "Docker must not publish a partial dependency install"
