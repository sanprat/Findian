import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Mock tavily module before importing tools
sys.modules['tavily'] = MagicMock()

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.core.tools import TavilyClient

class TestTavilyClient(unittest.TestCase):
    def setUp(self):
        self.client = TavilyClient()

    @patch('backend.app.core.tools.BaseTavilyClient')
    def test_search_news_failover(self, MockBaseClient):
        # Setup Mock
        mock_instance = MockBaseClient.return_value
        
        # Scenario: First key fails, Second key succeeds
        # We need self.client.available_keys to have at least 2 keys
        self.client.available_keys = ["key1", "key2"]
        
        # First call raises Exception
        # Second call returns success
        mock_instance.search.side_effect = [Exception("Key 1 Invalid"), {"results": [{"title": "Test News", "url": "http://test.com", "content": "News Content"}]}]
        
        result = self.client.search_news("Test Query")
        
        self.assertIn("Test News", result)
        self.assertIn("http://test.com", result)
        
        # Verify BaseTavilyClient was initialized twice (once for key1, once for key2)
        self.assertEqual(MockBaseClient.call_count, 2)

    def test_search_no_keys(self):
        self.client.available_keys = []
        result = self.client.search_news("Test")
        self.assertIn("No search API keys configured", result)

if __name__ == '__main__':
    unittest.main()
