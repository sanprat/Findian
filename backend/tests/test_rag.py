import unittest
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.core.rag import RAGService

class TestRAGService(unittest.TestCase):
    def setUp(self):
        self.test_data = "backend/tests/test_knowledge.json"
        self.test_persist = "backend/tests/test_chroma_db"
        
        # Create dummy knowledge base
        import json
        with open(self.test_data, "w") as f:
            json.dump([
                {"term": "TestTerm", "definition": "This is a test definition.", "category": "Test"}
            ], f)
            
        # Mock CHUTES_API_TOKEN
        os.environ["CHUTES_API_TOKEN"] = "test_token"
        
        self.rag = RAGService(data_path=self.test_data, persist_dir=self.test_persist)

    def tearDown(self):
        if os.path.exists(self.test_data):
            os.remove(self.test_data)
            
        import shutil
        if os.path.exists(self.test_persist):
            shutil.rmtree(self.test_persist)

    @patch("backend.app.core.rag.httpx.post")
    def test_ingest_and_query(self, mock_post):
        # Mock embeddings response from Chutes
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1] * 768}
            ]
        }
        mock_post.return_value = mock_response

        # Test Ingestion
        try:
            self.rag.ingest_knowledge_base()
        except Exception as e:
            self.fail(f"Ingestion failed: {e}")
            
        # Update mock for query (it calls get_embeddings again)
        mock_post.return_value = mock_response

        # Test Query
        try:
            result = self.rag.query("TestTerm")
            self.assertIn("TestTerm", result)
            self.assertIn("This is a test definition", result)
        except Exception as e:
            self.fail(f"Query failed: {e}")

if __name__ == '__main__':
    unittest.main()
