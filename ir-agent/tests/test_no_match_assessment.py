ALICE = {"Authorization": "Bearer tok-alice"}


def test_no_match_query_assessment(client):
    print("\n=== IR-08: No-match query handling ===")

    created = client.post(
        "/datasources",
        headers=ALICE,
        json={
            "name": "IR08 Synthetic Astronomy Document",
            "description": "Astronomy content",
            "content": (
                "Exoplanet spectroscopy detects atmospheric "
                "molecules around distant planetary systems."
            ),
            "source_type": "document",
        },
    )

    assert created.status_code in (200, 201), created.text
    document_id = created.json()["id"]

    try:
        query = "quantum cryptographic lattice signatures"
        response = client.post(
            "/search",
            headers=ALICE,
            json={"query": query, "top_k": 10},
        )

        print("Query:", query)
        print("HTTP status:", response.status_code)
        assert response.status_code == 200, response.text

        results = response.json().get("results", [])
        print("Returned result count:", len(results))

        for result in results:
            print(
                "Returned:",
                result.get("name"),
                "| score:",
                result.get("score"),
            )

        matching_synthetic_document = any(
            result.get("datasource_id") == document_id
            for result in results
        )

        print(
            "Unrelated astronomy document returned:",
            matching_synthetic_document,
        )

        assert not matching_synthetic_document, (
            "The unrelated astronomy document appeared in the results."
        )

        print(
            "Conclusion: the synthetic unrelated document was not returned "
            "for this query."
        )

    finally:
        client.delete(
            f"/datasources/{document_id}",
            headers=ALICE,
        )
