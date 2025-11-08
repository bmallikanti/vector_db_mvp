"""
CRUD tests for Vector DB API endpoints.
Tests are independent of Temporal workflows - they test direct CRUD operations only.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestLibrariesCRUD:
    """Test CRUD operations for Libraries."""

    def test_create_library_minimal(self):
        """Test creating a library with minimal data (name only)."""
        response = client.post(
            "/vector_db/libraries",
            json={"name": "Test Library"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Library"
        assert data["description"] is None
        assert "id" in data
        assert "metadata" in data

    def test_create_library_full(self):
        """Test creating a library with all fields."""
        response = client.post(
            "/vector_db/libraries",
            json={
                "name": "Full Library",
                "description": "A complete library",
                "metadata": {"tags": "test,demo"}
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Full Library"
        assert data["description"] == "A complete library"
        assert data["metadata"]["tags"] == "test,demo"

    def test_list_libraries(self):
        """Test listing all libraries."""
        # Create a couple of libraries first
        client.post("/vector_db/libraries", json={"name": "Lib 1"})
        client.post("/vector_db/libraries", json={"name": "Lib 2"})
        
        response = client.get("/vector_db/libraries")
        assert response.status_code == 200
        libraries = response.json()
        assert isinstance(libraries, list)
        assert len(libraries) >= 2

    def test_get_library(self):
        """Test getting a specific library."""
        # Create a library
        create_response = client.post(
            "/vector_db/libraries",
            json={"name": "Get Test Library"}
        )
        lib_id = create_response.json()["id"]
        
        # Get it
        response = client.get(f"/vector_db/libraries/{lib_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == lib_id
        assert data["name"] == "Get Test Library"

    def test_get_library_not_found(self):
        """Test getting a non-existent library returns 404."""
        response = client.get("/vector_db/libraries/non-existent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_library(self):
        """Test updating a library."""
        # Create a library
        create_response = client.post(
            "/vector_db/libraries",
            json={"name": "Original Name"}
        )
        lib_id = create_response.json()["id"]
        
        # Update it
        response = client.put(
            f"/vector_db/libraries/{lib_id}",
            json={
                "name": "Updated Name",
                "description": "Updated description",
                "metadata": {"tags": "updated"}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["metadata"]["tags"] == "updated"

    def test_update_library_missing_name(self):
        """Test updating a library without name returns 400."""
        create_response = client.post(
            "/vector_db/libraries",
            json={"name": "Test"}
        )
        lib_id = create_response.json()["id"]
        
        response = client.put(
            f"/vector_db/libraries/{lib_id}",
            json={"description": "No name"}
        )
        assert response.status_code == 400

    def test_update_library_not_found(self):
        """Test updating a non-existent library returns 404."""
        response = client.put(
            "/vector_db/libraries/non-existent-id",
            json={"name": "Test"}
        )
        assert response.status_code == 404

    def test_delete_library(self):
        """Test deleting a library."""
        # Create a library
        create_response = client.post(
            "/vector_db/libraries",
            json={"name": "To Delete"}
        )
        lib_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(f"/vector_db/libraries/{lib_id}")
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = client.get(f"/vector_db/libraries/{lib_id}")
        assert get_response.status_code == 404

    def test_delete_library_not_found(self):
        """Test deleting a non-existent library returns 404."""
        response = client.delete("/vector_db/libraries/non-existent-id")
        assert response.status_code == 404


class TestDocumentsCRUD:
    """Test CRUD operations for Documents."""

    @pytest.fixture(autouse=True)
    def setup_library(self):
        """Create a library for each test."""
        response = client.post(
            "/vector_db/libraries",
            json={"name": "Test Library for Documents"}
        )
        lib_id = response.json()["id"]
        yield lib_id
        # Cleanup: delete the library (which should cascade delete documents)
        client.delete(f"/vector_db/libraries/{lib_id}")

    def test_create_document_minimal(self, setup_library):
        """Test creating a document with minimal data."""
        lib_id = setup_library
        response = client.post(
            f"/vector_db/libraries/{lib_id}/documents",
            json={"title": "Test Document"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Document"
        assert "id" in data
        assert "metadata" in data

    def test_create_document_full(self, setup_library):
        """Test creating a document with all fields."""
        lib_id = setup_library
        response = client.post(
            f"/vector_db/libraries/{lib_id}/documents",
            json={
                "title": "Full Document",
                "metadata": {"category": "test"}
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Full Document"
        assert data["metadata"]["category"] == "test"

    def test_create_document_library_not_found(self):
        """Test creating a document in non-existent library returns 404."""
        response = client.post(
            "/vector_db/libraries/non-existent-id/documents",
            json={"title": "Test"}
        )
        assert response.status_code == 404

    def test_list_documents(self, setup_library):
        """Test listing documents in a library."""
        lib_id = setup_library
        # Create a couple of documents
        client.post(
            f"/vector_db/libraries/{lib_id}/documents",
            json={"title": "Doc 1"}
        )
        client.post(
            f"/vector_db/libraries/{lib_id}/documents",
            json={"title": "Doc 2"}
        )
        
        response = client.get(f"/vector_db/libraries/{lib_id}/documents")
        assert response.status_code == 200
        documents = response.json()
        assert isinstance(documents, list)
        assert len(documents) >= 2

    def test_list_documents_library_not_found(self):
        """Test listing documents from non-existent library returns 404."""
        response = client.get("/vector_db/libraries/non-existent-id/documents")
        assert response.status_code == 404

    def test_get_document(self, setup_library):
        """Test getting a specific document."""
        lib_id = setup_library
        # Create a document
        create_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents",
            json={"title": "Get Test Document"}
        )
        doc_id = create_response.json()["id"]
        
        # Get it
        response = client.get(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id
        assert data["title"] == "Get Test Document"

    def test_get_document_not_found(self, setup_library):
        """Test getting a non-existent document returns 404."""
        lib_id = setup_library
        response = client.get(
            f"/vector_db/libraries/{lib_id}/documents/non-existent-id"
        )
        assert response.status_code == 404

    def test_update_document_title(self, setup_library):
        """Test updating a document's title."""
        lib_id = setup_library
        # Create a document
        create_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents",
            json={"title": "Original Title"}
        )
        doc_id = create_response.json()["id"]
        
        # Update it
        response = client.put(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}",
            json={"title": "Updated Title"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_update_document_metadata(self, setup_library):
        """Test updating a document's metadata."""
        lib_id = setup_library
        create_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents",
            json={"title": "Test Doc"}
        )
        doc_id = create_response.json()["id"]
        
        response = client.put(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}",
            json={"metadata": {"category": "updated"}}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["category"] == "updated"

    def test_update_document_no_fields(self, setup_library):
        """Test updating a document with no fields returns 400."""
        lib_id = setup_library
        create_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents",
            json={"title": "Test Doc"}
        )
        doc_id = create_response.json()["id"]
        
        response = client.put(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}",
            json={}
        )
        assert response.status_code == 400

    def test_update_document_not_found(self, setup_library):
        """Test updating a non-existent document returns 404."""
        lib_id = setup_library
        response = client.put(
            f"/vector_db/libraries/{lib_id}/documents/non-existent-id",
            json={"title": "Test"}
        )
        assert response.status_code == 404

    def test_delete_document(self, setup_library):
        """Test deleting a document."""
        lib_id = setup_library
        # Create a document
        create_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents",
            json={"title": "To Delete"}
        )
        doc_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}"
        )
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = client.get(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}"
        )
        assert get_response.status_code == 404

    def test_delete_document_not_found(self, setup_library):
        """Test deleting a non-existent document returns 404."""
        lib_id = setup_library
        response = client.delete(
            f"/vector_db/libraries/{lib_id}/documents/non-existent-id"
        )
        assert response.status_code == 404


class TestChunksCRUD:
    """Test CRUD operations for Chunks."""

    @pytest.fixture(autouse=True)
    def setup_library_and_document(self):
        """Create a library and document for each test."""
        # Create library
        lib_response = client.post(
            "/vector_db/libraries",
            json={"name": "Test Library for Chunks"}
        )
        lib_id = lib_response.json()["id"]
        
        # Create document
        doc_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents",
            json={"title": "Test Document for Chunks"}
        )
        doc_id = doc_response.json()["id"]
        
        yield lib_id, doc_id
        
        # Cleanup: delete the library (which should cascade delete documents and chunks)
        client.delete(f"/vector_db/libraries/{lib_id}")

    def test_create_chunk_minimal(self, setup_library_and_document):
        """Test creating a chunk with minimal data."""
        lib_id, doc_id = setup_library_and_document
        response = client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={"text": "This is a test chunk"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["text"] == "This is a test chunk"
        assert "id" in data
        assert "metadata" in data

    def test_create_chunk_with_embedding(self, setup_library_and_document):
        """Test creating a chunk with embedding."""
        lib_id, doc_id = setup_library_and_document
        response = client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={
                "text": "Chunk with embedding",
                "embedding": [0.1, 0.2, 0.3, 0.4]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["text"] == "Chunk with embedding"
        assert data["embedding"] == [0.1, 0.2, 0.3, 0.4]

    def test_create_chunk_full(self, setup_library_and_document):
        """Test creating a chunk with all fields."""
        lib_id, doc_id = setup_library_and_document
        response = client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={
                "text": "Full chunk",
                "embedding": [0.5, 0.6],
                "metadata": {"type": "paragraph"}
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["text"] == "Full chunk"
        assert data["embedding"] == [0.5, 0.6]
        assert data["metadata"]["type"] == "paragraph"

    def test_create_chunk_library_not_found(self):
        """Test creating a chunk in non-existent library returns 404."""
        response = client.post(
            "/vector_db/libraries/non-existent-id/documents/doc-id/chunks",
            json={"text": "Test"}
        )
        assert response.status_code == 404

    def test_create_chunk_document_not_found(self, setup_library_and_document):
        """Test creating a chunk in non-existent document returns 404."""
        lib_id, _ = setup_library_and_document
        response = client.post(
            f"/vector_db/libraries/{lib_id}/documents/non-existent-id/chunks",
            json={"text": "Test"}
        )
        assert response.status_code == 404

    def test_list_chunks(self, setup_library_and_document):
        """Test listing chunks in a document."""
        lib_id, doc_id = setup_library_and_document
        # Create a couple of chunks
        client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={"text": "Chunk 1"}
        )
        client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={"text": "Chunk 2"}
        )
        
        response = client.get(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks"
        )
        assert response.status_code == 200
        chunks = response.json()
        assert isinstance(chunks, list)
        assert len(chunks) >= 2

    def test_list_chunks_library_not_found(self):
        """Test listing chunks from non-existent library returns 404."""
        response = client.get(
            "/vector_db/libraries/non-existent-id/documents/doc-id/chunks"
        )
        assert response.status_code == 404

    def test_list_chunks_document_not_found(self, setup_library_and_document):
        """Test listing chunks from non-existent document returns 404."""
        lib_id, _ = setup_library_and_document
        response = client.get(
            f"/vector_db/libraries/{lib_id}/documents/non-existent-id/chunks"
        )
        assert response.status_code == 404

    def test_update_chunk_text(self, setup_library_and_document):
        """Test updating a chunk's text."""
        lib_id, doc_id = setup_library_and_document
        # Create a chunk
        create_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={"text": "Original text"}
        )
        chunk_id = create_response.json()["id"]
        
        # Update it
        response = client.put(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks/{chunk_id}",
            json={"text": "Updated text"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Updated text"

    def test_update_chunk_embedding(self, setup_library_and_document):
        """Test updating a chunk's embedding."""
        lib_id, doc_id = setup_library_and_document
        create_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={"text": "Test chunk", "embedding": [1.0, 2.0]}
        )
        chunk_id = create_response.json()["id"]
        
        response = client.put(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks/{chunk_id}",
            json={"embedding": [3.0, 4.0]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["embedding"] == [3.0, 4.0]

    def test_update_chunk_metadata(self, setup_library_and_document):
        """Test updating a chunk's metadata."""
        lib_id, doc_id = setup_library_and_document
        create_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={"text": "Test chunk"}
        )
        chunk_id = create_response.json()["id"]
        
        response = client.put(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks/{chunk_id}",
            json={"metadata": {"type": "heading"}}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["type"] == "heading"

    def test_update_chunk_no_fields(self, setup_library_and_document):
        """Test updating a chunk with no fields returns 400."""
        lib_id, doc_id = setup_library_and_document
        create_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={"text": "Test chunk"}
        )
        chunk_id = create_response.json()["id"]
        
        response = client.put(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks/{chunk_id}",
            json={}
        )
        assert response.status_code == 400

    def test_update_chunk_not_found(self, setup_library_and_document):
        """Test updating a non-existent chunk returns 404."""
        lib_id, doc_id = setup_library_and_document
        response = client.put(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks/non-existent-id",
            json={"text": "Test"}
        )
        assert response.status_code == 404

    def test_delete_chunk(self, setup_library_and_document):
        """Test deleting a chunk."""
        lib_id, doc_id = setup_library_and_document
        # Create a chunk
        create_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={"text": "To Delete"}
        )
        chunk_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks/{chunk_id}"
        )
        assert response.status_code == 204
        
        # Verify it's gone (by checking list is empty or doesn't contain it)
        list_response = client.get(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks"
        )
        chunks = list_response.json()
        chunk_ids = [c["id"] for c in chunks]
        assert chunk_id not in chunk_ids

    def test_delete_chunk_not_found(self, setup_library_and_document):
        """Test deleting a non-existent chunk returns 404."""
        lib_id, doc_id = setup_library_and_document
        response = client.delete(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks/non-existent-id"
        )
        assert response.status_code == 404


class TestCRUDIntegration:
    """Integration tests for CRUD operations across all entities."""

    def test_full_crud_workflow(self):
        """Test a complete workflow: create library -> document -> chunks -> update -> delete."""
        # Create library
        lib_response = client.post(
            "/vector_db/libraries",
            json={"name": "Integration Test Library"}
        )
        assert lib_response.status_code == 201
        lib_id = lib_response.json()["id"]
        
        # Create document
        doc_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents",
            json={"title": "Integration Test Document"}
        )
        assert doc_response.status_code == 201
        doc_id = doc_response.json()["id"]
        
        # Create chunks
        chunk1_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={"text": "First chunk", "embedding": [0.1, 0.2]}
        )
        assert chunk1_response.status_code == 201
        chunk1_id = chunk1_response.json()["id"]
        
        chunk2_response = client.post(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks",
            json={"text": "Second chunk", "embedding": [0.3, 0.4]}
        )
        assert chunk2_response.status_code == 201
        
        # List chunks
        chunks_response = client.get(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks"
        )
        assert chunks_response.status_code == 200
        chunks = chunks_response.json()
        assert len(chunks) == 2
        
        # Update chunk
        update_response = client.put(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks/{chunk1_id}",
            json={"text": "Updated first chunk"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["text"] == "Updated first chunk"
        
        # Delete chunk
        delete_chunk_response = client.delete(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks/{chunk1_id}"
        )
        assert delete_chunk_response.status_code == 204
        
        # Verify chunk is deleted
        chunks_response = client.get(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks"
        )
        chunks = chunks_response.json()
        assert len(chunks) == 1
        
        # Delete document
        delete_doc_response = client.delete(
            f"/vector_db/libraries/{lib_id}/documents/{doc_id}"
        )
        assert delete_doc_response.status_code == 204
        
        # Delete library
        delete_lib_response = client.delete(f"/vector_db/libraries/{lib_id}")
        assert delete_lib_response.status_code == 204
        
        # Verify everything is deleted
        get_lib_response = client.get(f"/vector_db/libraries/{lib_id}")
        assert get_lib_response.status_code == 404

