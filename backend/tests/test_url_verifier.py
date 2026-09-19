import pytest
from backend.app.services.url_verifier import url_verifier

def test_url_syntax_check():
    assert url_verifier.is_valid_url_syntax("https://sponsorajobs.com/jobs/123") is True
    assert url_verifier.is_valid_url_syntax("http://localhost:8000/test") is True
    assert url_verifier.is_valid_url_syntax("not-a-valid-url") is False
    assert url_verifier.is_valid_url_syntax("ftp://invalid.domain/file") is True
    assert url_verifier.is_valid_url_syntax("") is False

@pytest.mark.asyncio
async def test_invalid_url_verification():
    res = await url_verifier.verify_url("invalid-url-path")
    assert res["status"] == "DEAD"
    assert "syntax" in res["message"].lower()
