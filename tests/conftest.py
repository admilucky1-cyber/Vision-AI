"""Keep application tests away from configured production databases."""
import os
import secrets
from tempfile import TemporaryDirectory

_test_data = TemporaryDirectory(prefix="vision-ai-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_data.name}/test.db"
os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["ALLOWED_HOSTS"] = "testserver"
os.environ["DEBUG"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["ADMIN_USERNAME"] = ""
os.environ["ADMIN_PASSWORD"] = ""


def pytest_sessionfinish(session, exitstatus):
    _test_data.cleanup()
