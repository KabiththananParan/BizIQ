ALICE = {"Authorization": "Bearer tok-alice"}


def test_api_error_handling_assessment(client):
    cases = [
        ("Malformed JSON", "{not-valid-json", "application/json"),
        ("Wrong content type", '{"query":"sales"}', "text/plain"),
        ("Query is a number", '{"query":123}', "application/json"),
        ("Top-k is a string", '{"query":"sales","top_k":"many"}',
         "application/json"),
    ]

    print("\n=== IR-03: API error handling ===")

    for label, body, content_type in cases:
        response = client.post(
            "/search",
            content=body,
            headers={
                **ALICE,
                "Content-Type": content_type,
            },
        )

        print(f"\n{label}: HTTP {response.status_code}")
        print("Response:", response.text[:500])

        assert response.status_code in (400, 415, 422), (
            f"Unexpected status for {label}: {response.status_code}"
        )

        lowered = response.text.lower()
        leaked_markers = [
            "traceback",
            "c:\\users\\",
            "sqlite3.operationalerror",
            "site-packages",
        ]

        found = [marker for marker in leaked_markers if marker in lowered]
        print("Internal detail markers found:", found or "None")
