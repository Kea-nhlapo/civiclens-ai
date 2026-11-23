import pytest

from app import main
from app.utils.rate_limit import Limits, RateLimiter


@pytest.fixture(autouse=True)
def no_photo_limits(monkeypatch) -> None:
    # The suite sends far more photos than a visitor may; the limiter has its own tests.
    monkeypatch.setattr(main, "limiter", RateLimiter(Limits(per_minute=10_000, per_day=10_000, global_per_day=10_000)))
