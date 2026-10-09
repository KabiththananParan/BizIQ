ALICE = {"Authorization": "Bearer tok-alice"}


def test_datasource_content_confidentiality(client):
    print("\n=== IR-14: Datasource content confidentiality ===")

    secret_marker = "IR14_SYNTHETIC_PRIVATE_CONTENT_8f2a1"

    created = client.post(
        "/datasources",
        headers=ALICE,
        json={
            "name": "IR14 Synthetic Confidentiality Test",
            "description": "Metadata exposure assessment",
            "content": f"Internal synthetic text: {secret_marker}",
            "source_type": "document",
        },
    )

    assert created.status_code == 201, created.text
    document_id = created.json()["id"]

    try:
        list_response = client.get(
            "/datasources",
            headers=ALICE,
        )
        detail_response = client.get(
            f"/datasources/{document_id}",
            headers=ALICE,
        )

        print("List response:", list_response.status_code)
        print("Detail response:", detail_response.status_code)

        assert list_response.status_code == 200, list_response.text
        assert detail_response.status_code == 200, detail_response.text

        listed = next(
            item for item in list_response.json()
            if item.get("id") == document_id
        )
        detailed = detail_response.json()

        print("Content field in list response:", "content" in listed)
        print("Content field in detail response:", "content" in detailed)
        print(
            "Synthetic private marker exposed in list:",
            secret_marker in list_response.text,
        )
        print(
            "Synthetic private marker exposed in detail:",
            secret_marker in detail_response.text,
        )

        assert "content" not in listed
        assert secret_marker not in list_response.text
        assert "content" not in detailed
        assert secret_marker not in detail_response.text

        print(
            "Conclusion: tested metadata endpoints did not expose "
            "the full datasource content."
        )

    finally:
        client.delete(
            f"/datasources/{document_id}",
            headers=ALICE,
        )
