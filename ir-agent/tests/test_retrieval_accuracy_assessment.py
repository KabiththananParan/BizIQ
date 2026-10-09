ALICE = {"Authorization": "Bearer tok-alice"}


def test_retrieval_accuracy_assessment(client):
    print("\n=== IR-07: Retrieval accuracy and ranking ===")

    documents = [
        {
            "name": "IR07 Relevant Sales Report",
            "description": "Quarterly sales performance",
            "content": (
                "The quarterly sales report shows revenue increased "
                "by 15 percent in the western region."
            ),
            "source_type": "document",
        },
        {
            "name": "IR07 Relevant Revenue Report",
            "description": "Revenue and sales analysis",
            "content": (
                "Regional revenue growth was driven by higher "
                "quarterly sales and customer demand."
            ),
            "source_type": "document",
        },
        {
            "name": "IR07 Irrelevant Gardening Report",
            "description": "Gardening and plants",
            "content": (
                "Tomato plants require sunlight, water, healthy soil, "
                "and regular pruning."
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
            assert response.status_code in (200, 201), response.text
            created_ids.append(response.json()["id"])

        query = "quarterly sales revenue growth"
        response = client.post(
            "/search",
            headers=ALICE,
            json={"query": query, "top_k": 10},
        )

        print("Query:", query)
        print("HTTP status:", response.status_code)
        assert response.status_code == 200, response.text

        results = response.json().get("results", [])
        for rank, result in enumerate(results, start=1):
            print(
                f"Rank {rank}: {result.get('name')} | "
                f"score={result.get('score')}"
            )

        names = [result.get("name", "") for result in results]
        relevant_names = {
            "IR07 Relevant Sales Report",
            "IR07 Relevant Revenue Report",
        }

        relevant_positions = [
            names.index(name)
            for name in relevant_names
            if name in names
        ]
        irrelevant_position = (
            names.index("IR07 Irrelevant Gardening Report")
            if "IR07 Irrelevant Gardening Report" in names
            else None
        )

        print("Relevant documents retrieved:", len(relevant_positions), "/ 2")
        print("Irrelevant document retrieved:", irrelevant_position is not None)

        assert relevant_positions, (
            "No relevant document was retrieved for the sales query."
        )

        if irrelevant_position is not None:
            best_relevant_position = min(relevant_positions)
            print(
                "Best relevant rank:",
                best_relevant_position + 1,
            )
            print(
                "Irrelevant rank:",
                irrelevant_position + 1,
            )
            assert best_relevant_position < irrelevant_position, (
                "The irrelevant document ranked above the best relevant "
                "document."
            )

        print("Conclusion: at least one relevant document was retrieved.")

    finally:
        for document_id in created_ids:
            client.delete(
                f"/datasources/{document_id}",
                headers=ALICE,
            )
