ALICE = {"Authorization": "Bearer tok-alice"}


def test_control_character_sanitization(client):
    print("\n=== IR-13: Control-character sanitization ===")

    payload = {
        "name": "IR13 Clean\x00Name",
        "description": "Sanitization assessment",
        "content": "safe\x07content with control characters",
        "source_type": "document",
    }

    response = client.post(
        "/datasources",
        headers=ALICE,
        json=payload,
    )

    print("Create response:", response.status_code)
    assert response.status_code == 201, response.text

    document_id = response.json()["id"]

    try:
        data = response.json()

        print("Stored name:", repr(data.get("name")))
        print("Control character in name:", "\x00" in data.get("name", ""))

        assert "\x00" not in data.get("name", ""), (
            "NUL character was not removed from the datasource name."
        )

        fetched = client.get(
            f"/datasources/{document_id}",
            headers=ALICE,
        )

        assert fetched.status_code == 200, fetched.text

        print("Read-after-create status:", fetched.status_code)
        print(
            "Conclusion: the NUL character was removed from the "
            "stored name."
        )

    finally:
        client.delete(
            f"/datasources/{document_id}",
            headers=ALICE,
        )
