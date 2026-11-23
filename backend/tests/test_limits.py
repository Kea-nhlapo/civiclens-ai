import asyncio
from io import BytesIO

import httpx
import pytest
from PIL import Image

from app import main
from app.utils.image_utils import validate_image
from app.utils.rate_limit import Limits, RateLimiter, visitor_of


class Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


def image_bytes(fmt: str) -> bytes:
    out = BytesIO()
    Image.new("RGB", (8, 8)).save(out, format=fmt)
    return out.getvalue()


def test_a_burst_is_cut_off_then_allowed_again_after_a_minute() -> None:
    clock = Clock()
    limiter = RateLimiter(Limits(per_minute=3, per_day=100, global_per_day=100), clock)
    assert [limiter.check("a") for _ in range(3)] == [None, None, None]
    wait = limiter.check("a")
    assert wait is not None and 0 < wait <= 61
    assert limiter.check("b") is None  # someone else isn't affected
    clock.now += 61
    assert limiter.check("a") is None


def test_the_daily_cap_per_visitor() -> None:
    clock = Clock()
    limiter = RateLimiter(Limits(per_minute=100, per_day=2, global_per_day=100), clock)
    assert limiter.check("a") is None
    assert limiter.check("a") is None
    assert limiter.check("a") is not None
    clock.now += 86_401
    assert limiter.check("a") is None


def test_the_daily_cap_for_everyone_holds_even_with_new_addresses() -> None:
    limiter = RateLimiter(Limits(per_minute=100, per_day=100, global_per_day=3), Clock())
    assert [limiter.check(f"ip{i}") for i in range(3)] == [None, None, None]
    assert limiter.check("ip99") is not None


def test_a_refused_request_does_not_use_up_the_allowance() -> None:
    limiter = RateLimiter(Limits(per_minute=1, per_day=100, global_per_day=100), Clock())
    assert limiter.check("a") is None
    for _ in range(5):
        assert limiter.check("a") is not None
    assert len(limiter.everyone) == 1


def test_the_visitor_is_the_address_the_load_balancer_added() -> None:
    assert visitor_of("6.6.6.6, 203.0.113.9", "10.0.0.1") == "203.0.113.9"
    assert visitor_of(None, "10.0.0.1") == "10.0.0.1"
    assert visitor_of("", None) == "unknown"


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_jpeg_png_and_webp_are_accepted(fmt: str) -> None:
    assert validate_image(image_bytes(fmt)).startswith("image/")


@pytest.mark.parametrize("fmt", ["GIF", "BMP", "TIFF"])
def test_other_image_formats_are_refused(fmt: str) -> None:
    with pytest.raises(ValueError):
        validate_image(image_bytes(fmt))


async def post(files: dict, data: dict | None = None, headers: dict | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/api/analyze-report", files=files, data=data or {}, headers=headers or {})


def test_the_api_answers_429_with_retry_after_when_the_limit_is_hit(monkeypatch) -> None:
    monkeypatch.setattr(main, "limiter", RateLimiter(Limits(per_minute=0, per_day=10, global_per_day=10)))
    response = asyncio.run(post({"image": ("a.png", image_bytes("PNG"), "image/png")}))
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


def test_a_long_note_is_refused_before_any_detection(monkeypatch) -> None:
    monkeypatch.setattr(main, "limiter", RateLimiter(Limits(per_minute=10, per_day=10, global_per_day=10)))
    response = asyncio.run(post({"image": ("a.png", image_bytes("PNG"), "image/png")}, data={"notes": "x" * 501}))
    assert response.status_code == 422
