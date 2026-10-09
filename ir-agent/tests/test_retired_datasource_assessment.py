ALICE = {"Authorization": "Bearer tok-alice"}


def test_retired_datasource_exclusion(client):
    print("\n=== IR-09: Retired datasource exclusion ===")

    created = client.post(
        "/datasources",
        headers=ALICE,
        json={
            "name": "IR09 Synthetic Retired Document",
            "description": "Retired datasource assessment",
            "content": "unique_ir09_retirement_search_keyword",
            "source_type": "document",
        },
    )

    assert created.status_code == 201, created.text
    document_id = created.json()["id"]

    try:
        query = "unique_ir09_retirement_search_keyword"

        active_search = client.post(
            "/search",
            headers=ALICE,
            json={"query": query, "top_k": 10},
        )

        assert active_search.status_code == 200, active_search.text
        active_found = any(
            result.get("datasource_id") == document_id
            for result in active_search.json().get("results", [])
        )

        print("Document found while active:", active_found)
        assert active_found, (
            "Control check failed: active document was not retrieved."
        )

        update = client.put(
            f"/datasources/{document_id}",
            headers=ALICE,
            json={"status": "retired"},
        )

        print("Retire request status:", update.status_code)
        assert update.status_code == 200, update.text
        print("Stored status:", update.json().get("status"))
        assert update.json().get("status") == "retired"

        retired_search = client.post(
            "/search",
            headers=ALICE,
            json={"query": query, "top_k": 10},
        )

        assert retired_search.status_code == 200, retired_search.text
        retired_found = any(
            result.get("datasource_id") == document_id
            for result in retired_search.json().get("results", [])
        )

        print("Document found after retirement:", retired_found)
        assert not retired_found, (
            "Retired datasource still appeared in search results."
        )

        print(
            "Conclusion: the active document was searchable, "
            "but the retired document was excluded."
        )

    finally:
        client.delete(
            f"/datasources/{document_id}",
            headers=ALICE,
        )
