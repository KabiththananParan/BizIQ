ALICE = {"Authorization": "Bearer tok-alice"}


def test_query_length_boundaries(client):
    print("\n=== IR-11: Query length boundaries ===")

    cases = [
        ("One-character query", "a", 200),
        ("500-character query", "a" * 500, 200),
        ("501-character query", "a" * 501, 422),
        ("Empty query", "", 422),
        ("Whitespace-only query", "   ", 422),
    ]

    for label, query, expected_status in cases:
        response = client.post(
            "/search",
            headers=ALICE,
            json={"query": query},
        )

        print(
            f"{label}: HTTP {response.status_code} "
            f"(expected {expected_status})"
        )

        assert response.status_code == expected_status, (
            f"{label}: expected {expected_status}, "
            f"received {response.status_code}; response={response.text}"
        )

    print("Conclusion: tested query length boundaries behaved as expected.")
