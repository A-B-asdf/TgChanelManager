import pytest
from fastapi.testclient import TestClient
from content_scheduler.main import app

@pytest.fixture
def client():
    return TestClient(app)