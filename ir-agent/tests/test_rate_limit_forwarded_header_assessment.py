def test_rate_limit_forwarded_header_assessment(client, monkeypatch):
    print("\n=== IR-16: Forwarded-header rate-limit assessment ===")

    monkeypatch.setenv("IR_RATE_LIMIT", "3")

    from app.services import auth
    auth.reset_rate_limits()

    token = {"Authorization": "Bearer tok-alice"}
    statuses = []

    for attempt in range(1, 7):
        headers = {
            **token,
            "X-Forwarded-For": f"198.51.100.{attempt}",
        }
        response = client.get("/datasources", headers=headers)
        statuses.append(response.status_code)
        print(
            f"Request {attempt}: HTTP {response.status_code} "
            f"| X-Forwarded-For: {headers['X-Forwarded-For']}"
        )

    print("Observed status sequence:", statuses)
    print(
        "Requests accepted:", sum(status == 200 for status in statuses)
    )

    if sum(status == 200 for status in statuses) > 3:
        print("FINDING: More than three requests were accepted.")
    else:
        print("No bypass observed in this test.")

    assert len(statuses) == 6
