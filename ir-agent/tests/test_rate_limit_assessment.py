def test_rate_limit_assessment(client, monkeypatch):
    print("\n=== IR-10: Rate limiting assessment ===")

    monkeypatch.setenv("IR_RATE_LIMIT", "3")

    from app.services import auth
    auth.reset_rate_limits()

    headers = {"Authorization": "Bearer tok-alice"}
    statuses = []

    for attempt in range(1, 6):
        response = client.get("/datasources", headers=headers)
        statuses.append(response.status_code)
        print(f"Request {attempt}: HTTP {response.status_code}")

    print("Observed status sequence:", statuses)

    assert statuses[:3] == [200, 200, 200], (
        f"Unexpected response before limit: {statuses}"
    )
    assert statuses[3] == 429, (
        f"Expected rate limit on request 4, got {statuses[3]}"
    )
    assert statuses[4] == 429, (
        f"Expected continued rate limiting on request 5, got {statuses[4]}"
    )

    print(
        "Conclusion: requests beyond the configured limit "
        "were rejected with HTTP 429."
    )
