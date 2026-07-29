from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")
