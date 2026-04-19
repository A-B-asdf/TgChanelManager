import pytest
from fastapi.testclient import TestClient
from posting_service.main import app

@pytest.fixture
def client():
    return TestClient(app)