ALICE = {"Authorization": "Bearer tok-alice"}


def test_sql_injection_search_assessment(client):
    print("\n=== IR-06: SQL injection assessment ===")

    created = client.post(
        "/datasources",
        headers=ALICE,
        json={
            "name": "IR06 Synthetic SQL Test",
            "description": "SQL injection assessment document",
            "content": "unique_ir06_synthetic_database_record",
            "source_type": "document",
        },
    )

    print("Create synthetic record:", created.status_code)
    assert created.status_code in (200, 201), created.text

    document_id = created.json().get("id")
    assert document_id is not None, created.json()

    payloads = [
        "' OR '1'='1",
        "'; DROP TABLE datasources; --",
        "test' UNION SELECT * FROM datasources --",
    ]

    try:
        for payload in payloads:
            response = client.post(
                "/search",
                headers=ALICE,
                json={"query": payload, "top_k": 10},
            )

            print(
                f"Payload: {payload!r} | "
                f"HTTP {response.status_code}"
            )

            assert response.status_code == 200, response.text

            results = response.json().get("results", [])
            print("Returned result count:", len(results))

        owner_check = client.get(
            f"/datasources/{document_id}",
            headers=ALICE,
        )

        print("Synthetic record still exists:", owner_check.status_code == 200)
        assert owner_check.status_code == 200, owner_check.text

        print(
            "Conclusion: payloads were processed without causing "
            "an HTTP error, and the synthetic record remained available."
        )

    finally:
        client.delete(
            f"/datasources/{document_id}",
            headers=ALICE,
        )
