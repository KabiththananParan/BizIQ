ALICE = {"Authorization": "Bearer tok-alice"}


def test_top_k_boundaries(client):
    print("\n=== IR-12: top_k boundary validation ===")

    cases = [
        ("Minimum top_k", 1, 200),
        ("Maximum top_k", 20, 200),
        ("Zero top_k", 0, 422),
        ("Negative top_k", -1, 422),
        ("Above maximum", 21, 422),
    ]

    for label, top_k, expected_status in cases:
        response = client.post(
            "/search",
            headers=ALICE,
            json={"query": "synthetic validation test", "top_k": top_k},
        )

        print(
            f"{label} ({top_k}): HTTP {response.status_code}; "
            f"expected {expected_status}"
        )

        assert response.status_code == expected_status, (
            f"{label}: expected {expected_status}, "
            f"received {response.status_code}; response={response.text}"
        )

        if response.status_code == 200:
            results = response.json().get("results", [])
            print("  Results returned:", len(results))
            assert len(results) <= top_k, (
                f"Returned {len(results)} results when top_k={top_k}"
            )

    print("Conclusion: tested top_k boundaries behaved as expected.")
