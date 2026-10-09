def test_cross_user_access_methods_assessment(client):
    alice = {"Authorization": "Bearer tok-alice"}
    bob = {"Authorization": "Bearer tok-bob"}

    created_id = None

    try:
        created = client.post(
            "/datasources",
            json={
                "name": "IR17 Alice Private Record",
                "content": "Synthetic private marker: cobalt-orion-8421",
            },
            headers=alice,
        )
        assert created.status_code == 201, created.text
        created_id = created.json()["id"]

        get_response = client.get(
            f"/datasources/{created_id}", headers=bob
        )
        put_response = client.put(
            f"/datasources/{created_id}",
            json={
                "name": "Modified by Bob",
                "content": "Unauthorized modification attempt",
            },
            headers=bob,
        )
        delete_response = client.delete(
            f"/datasources/{created_id}", headers=bob
        )

        alice_after = client.get(
            f"/datasources/{created_id}", headers=alice
        )

        print("\n=== IR-17: Cross-user access methods ===")
        print("Bob GET:", get_response.status_code)
        print("Bob PUT:", put_response.status_code)
        print("Bob DELETE:", delete_response.status_code)
        print("Alice GET after attempts:", alice_after.status_code)

        if alice_after.status_code == 200:
            print("Alice's record remains accessible.")
            print(
                "Record name after attempts:",
                alice_after.json().get("name"),
            )

        assert get_response.status_code == 404
        assert put_response.status_code == 404
        assert delete_response.status_code == 404

    finally:
        if created_id is not None:
            client.delete(
                f"/datasources/{created_id}", headers=alice
            )
