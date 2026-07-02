import asyncio

import httpx
from app.main import app


async def request(method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_health() -> None:
    response = asyncio.run(request("GET", "/health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "CivicLens AI Backend"}


def test_root() -> None:
    response = asyncio.run(request("GET", "/"))
    assert response.status_code == 200
    assert response.json() == {"message": "CivicLens AI Backend is running"}
