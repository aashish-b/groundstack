from service.auth import refresh_token, should_refresh


def test_should_refresh_when_margin_crossed() -> None:
    assert should_refresh(120.0, now=61.0)


def test_refresh_token_uses_fetch_session(fake_client) -> None:
    token = refresh_token(fake_client, "refresh-token")
    assert token == "new-access-token"
