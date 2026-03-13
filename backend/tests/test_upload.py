"""Tests for upload endpoints."""

import io

import pytest
from fastapi.testclient import TestClient


class TestUploadPreview:
    """Tests for upload preview endpoint."""

    def test_preview_csv(self, client: TestClient):
        """Test CSV file preview."""
        content = b"name,age,city\nAlice,30,NYC\nBob,25,LA"
        files = {"file": ("test.csv", io.BytesIO(content), "text/csv")}

        response = client.post("/api/v1/upload/preview", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "metadata" in data
        assert "columns" in data
        assert "data" in data
        assert len(data["columns"]) == 3
        assert len(data["data"]) == 2

    def test_preview_unsupported_type(self, client: TestClient):
        """Test that unsupported file types are rejected."""
        content = b'{"name": "test"}'
        files = {"file": ("test.json", io.BytesIO(content), "application/json")}

        response = client.post("/api/v1/upload/preview", files=files)

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_preview_with_limit(self, client: TestClient):
        """Test preview with row limit."""
        content = b"id\n1\n2\n3\n4\n5"
        files = {"file": ("test.csv", io.BytesIO(content), "text/csv")}

        response = client.post(
            "/api/v1/upload/preview",
            files=files,
            params={"preview_rows": 2},
        )

        assert response.status_code == 200
        assert len(response.json()["data"]) == 2


class TestUploadFile:
    """Tests for file upload endpoint."""

    def test_upload_csv(self, client: TestClient):
        """Test uploading a CSV file."""
        content = b"id,name,value\n1,Alice,100\n2,Bob,200"
        files = {"file": ("test.csv", io.BytesIO(content), "text/csv")}

        response = client.post(
            "/api/v1/upload/",
            files=files,
            data={"source_name": "Test Source"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source_name"] == "Test Source"
        assert data["source_type"] == "csv"
        assert "id" in data

    def test_upload_with_description(self, client: TestClient):
        """Test upload with description."""
        content = b"a,b\n1,2"
        files = {"file": ("data.csv", io.BytesIO(content), "text/csv")}

        response = client.post(
            "/api/v1/upload/",
            files=files,
            data={
                "source_name": "My Data",
                "description": "Test data for upload",
            },
        )

        assert response.status_code == 200
        assert response.json()["description"] == "Test data for upload"

    def test_upload_uses_filename_as_default_name(self, client: TestClient):
        """Test that filename is used as default source name."""
        content = b"x,y\n1,2"
        files = {"file": ("my_data.csv", io.BytesIO(content), "text/csv")}

        response = client.post("/api/v1/upload/", files=files)

        assert response.status_code == 200
        assert response.json()["source_name"] == "my_data.csv"
