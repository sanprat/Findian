import unittest
import os
import sys
from unittest.mock import MagicMock

# Mock leann module before importing rag
sys.modules['leann'] = MagicMock()

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.core.rag import RAGService

class TestRAGService(unittest.TestCase):
    def setUp(self):
        self.test_data = "backend/tests/test_knowledge.json"
        self.test_index = "backend/tests/test_education.leann"
        
        # Create dummy knowledge base
        with open(self.test_data, "w") as f:
            f.write('[{"term": "TestTerm", "definition": "This is a test definition.", "category": "Test"}]')
            
        self.rag = RAGService(data_path=self.test_data, index_path=self.test_index)

    def tearDown(self):
        if os.path.exists(self.test_data):
            os.remove(self.test_data)
        # Clean up leann index if it creates a file/folder
        # Leann behavior unknown, assuming file for now
        if os.path.exists(self.test_index):
            os.remove(self.test_index)

    def test_ingest_and_query(self):
        # Configure Mock for search
        # We need to access the mock we injected into sys.modules['leann']
        import leann
        mock_searcher = leann.LeannSearcher.return_value
        mock_searcher.search.return_value = ["TestTerm (Test): This is a test definition."]

        # Test Ingestion
        try:
            self.rag.ingest_knowledge_base()
        except Exception as e:
            self.fail(f"Ingestion failed: {e}")
            
        # Test Query
        try:
            result = self.rag.query("TestTerm")
            self.assertIn("TestTerm", result)
            self.assertIn("This is a test definition", result)
        except Exception as e:
            self.fail(f"Query failed: {e}")

if __name__ == '__main__':
    unittest.main()
