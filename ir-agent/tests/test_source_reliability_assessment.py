ALICE = {"Authorization": "Bearer tok-alice"}


def test_conflicting_source_reliability_assessment(client):
    print("\n=== IR-15: Conflicting source reliability ===")

    documents = [
        {
            "name": "IR15 Official Quarterly Sales Report",
            "description": "Synthetic source labelled official",
            "content": (
                "Quarterly sales report: western region revenue "
                "decreased by 12 percent during the third quarter."
            ),
            "source_type": "document",
        },
        {
            "name": "IR15 Unverified Sales Claim",
            "description": "Synthetic source labelled unverified",
            "content": (
                "Quarterly sales report: western region revenue "
                "increased by 90 percent during the third quarter."
            ),
            "source_type": "document",
        },
    ]

    created_ids = []

    try:
        for document in documents:
            response = client.post(
                "/datasources",
                headers=ALICE,
                json=document,
            )
            assert response.status_code == 201, response.text
            created_ids.append(response.json()["id"])

        query = "western region quarterly sales revenue third quarter"
        response = client.post(
            "/search",
            headers=ALICE,
            json={"query": query, "top_k": 10},
        )

        assert response.status_code == 200, response.text
        results = response.json().get("results", [])

        print("Query:", query)

        for rank, result in enumerate(results, start=1):
            if result.get("datasource_id") in created_ids:
                print(
                    f"Rank {rank}: {result.get('name')} | "
                    f"score={result.get('score')}"
                )

        official_found = any(
            result.get("datasource_id") == created_ids[0]
            for result in results
        )
        unverified_found = any(
            result.get("datasource_id") == created_ids[1]
            for result in results
        )

        print("Official-labelled source retrieved:", official_found)
        print("Unverified-labelled source retrieved:", unverified_found)

        assert official_found and unverified_found, (
            "Both conflicting synthetic sources should be retrievable."
        )

        print(
            "Observation: retrieval returned both conflicting sources. "
            "Ranking scores alone do not establish factual reliability."
        )

    finally:
        for document_id in created_ids:
            client.delete(
                f"/datasources/{document_id}",
                headers=ALICE,
            )
