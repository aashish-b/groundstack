def fetch_session(client: object, refresh_token_value: str) -> dict[str, str]:
    response = client.post(
        "/oauth/token",
        json={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token_value,
        },
    )
    return response.json()
