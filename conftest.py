import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database
from database import Base
from main import app


@pytest.fixture
def client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite:///{path}"
    test_engine = create_engine(url, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    test_engine.dispose()
    os.unlink(path)


@pytest.fixture
def auth_headers(client):
    client.post("/auth/register", json={"email": "u@example.com", "password": "password1"})
    resp = client.post("/auth/login", json={"email": "u@example.com", "password": "password1"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
