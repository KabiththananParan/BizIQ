ALICE = {"Authorization": "Bearer tok-alice"}
BOB = {"Authorization": "Bearer tok-bob"}


def test_cross_user_modification_assessment(client):
    print("\n=== IR-05: Cross-user modification protection ===")

    created = client.post(
        "/datasources",
        headers=ALICE,
        json={
            "name": "IR05 Synthetic Alice Document",
            "description": "Authorization assessment",
            "content": "unique_ir05_authorization_sample",
            "source_type": "document",
        },
    )

    print("Alice create:", created.status_code)
    assert created.status_code in (200, 201), created.text

    data = created.json()
    document_id = data.get("id")
    assert document_id is not None, data

    try:
        update = client.put(
            f"/datasources/{document_id}",
            headers=BOB,
            json={"name": "Modified by Bob"},
        )

        print("Bob update:", update.status_code)
        assert update.status_code in (403, 404), update.text

        check = client.get(
            f"/datasources/{document_id}",
            headers=ALICE,
        )

        print("Alice read after Bob update:", check.status_code)
        assert check.status_code == 200, check.text
        assert check.json().get("name") == "IR05 Synthetic Alice Document"

        delete = client.delete(
            f"/datasources/{document_id}",
            headers=BOB,
        )

        print("Bob delete:", delete.status_code)
        assert delete.status_code in (403, 404), delete.text

        check_after_delete = client.get(
            f"/datasources/{document_id}",
            headers=ALICE,
        )

        print("Alice read after Bob delete:", check_after_delete.status_code)
        assert check_after_delete.status_code == 200, check_after_delete.text

        print("Conclusion: Bob could not modify or delete Alice's document.")

    finally:
        client.delete(
            f"/datasources/{document_id}",
            headers=ALICE,
        )
