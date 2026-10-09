def test_authentication_bypass_assessment(client):
    cases = [
        ("No Authorization header", {}),
        ("Invalid bearer token",
         {"Authorization": "Bearer invalid-token-xyz"}),
        ("Basic authentication",
         {"Authorization": "Basic dXNlcjpwYXNz"}),
        ("Empty bearer token",
         {"Authorization": "Bearer "}),
    ]

    print("\n=== IR-04: Authentication bypass checks ===")

    for label, headers in cases:
        response = client.post(
            "/search",
            json={"query": "synthetic authentication test"},
            headers=headers,
        )

        authenticated = response.status_code == 200
        print(
            f"{label}: HTTP {response.status_code} | "
            f"Protected endpoint accessible: {authenticated}"
        )

        assert response.status_code == 401, (
            f"{label} unexpectedly returned HTTP "
            f"{response.status_code}"
        )

    print("\nConclusion: all tested unauthenticated requests were rejected.")
