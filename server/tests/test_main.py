from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_read_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_backend_serves_swagger_ui() -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "CPS420 API - Swagger UI" in response.text
    assert "url: '/openapi.json'" in response.text


def test_openapi_describes_mfa_and_bearer_auth() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema["paths"]

    login = paths["/auth/login"]["post"]
    assert "application/x-www-form-urlencoded" in login["requestBody"]["content"]
    challenge = login["responses"]["202"]["content"]["application/json"]["schema"]
    assert {response["$ref"] for response in challenge["anyOf"]} == {
        "#/components/schemas/MFARequired",
        "#/components/schemas/MFASetupRequired",
    }
    assert "Set-Cookie" in login["responses"]["202"]["headers"]
    assert "Set-Cookie" in paths["/auth/register"]["post"]["responses"]["202"]["headers"]
    assert "Set-Cookie" in paths["/auth/login/verify"]["post"]["responses"]["200"]["headers"]
    assert "201" in paths["/auth/register/verify"]["post"]["responses"]

    bearer = schema["components"]["securitySchemes"]["BearerAuth"]
    assert (bearer["type"], bearer["scheme"], bearer["bearerFormat"]) == ("http", "bearer", "JWT")
    assert paths["/auth/me"]["get"]["security"] == [{"BearerAuth": []}]
    assert "/docs" not in paths
