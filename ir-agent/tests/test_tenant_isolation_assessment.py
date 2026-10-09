ALICE = {"Authorization": "Bearer tok-alice"}
BOB = {"Authorization": "Bearer tok-bob"}


def test_cross_user_retrieval_isolation_assessment(client):
    document = {
        "name": "IR02 Synthetic Alice Confidential Report",
        "content": (
            "Synthetic confidential project data: "
            "orion cobalt revenue forecast 7319. "
            "This is fictional security assessment data."
        ),
    }

    created_id = None

    try:
        create_response = client.post(
            "/datasources",
            json=document,
            headers=ALICE,
        )
        assert create_response.status_code == 201, create_response.text
        created_id = create_response.json()["id"]

        # Alice should be able to retrieve her own document.
        alice_search = client.post(
            "/search",
            json={"query": "orion cobalt revenue forecast"},
            headers=ALICE,
        )
        assert alice_search.status_code == 200
        alice_ids = {
            item["datasource_id"]
            for item in alice_search.json()["results"]
        }
        assert created_id in alice_ids

        # Bob should not retrieve Alice's document through search.
        bob_search = client.post(
            "/search",
            json={"query": "orion cobalt revenue forecast"},
            headers=BOB,
        )
        assert bob_search.status_code == 200
        bob_ids = {
            item["datasource_id"]
            for item in bob_search.json()["results"]
        }
        assert created_id not in bob_ids

        # Bob should not access the document directly by its ID.
        bob_get = client.get(
            f"/datasources/{created_id}",
            headers=BOB,
        )
        assert bob_get.status_code == 404

        print("\n=== IR-02: Cross-user isolation ===")
        print("Alice search:", alice_search.status_code,
              "| own document found:", created_id in alice_ids)
        print("Bob search:", bob_search.status_code,
              "| Alice document exposed:", created_id in bob_ids)
        print("Bob direct GET:", bob_get.status_code)

    finally:
        if created_id is not None:
            client.delete(
                f"/datasources/{created_id}",
                headers=ALICE,
            )
