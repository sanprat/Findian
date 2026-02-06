import os
import logging
from typing import List, Dict, Optional
from tavily import TavilyClient as BaseTavilyClient

logger = logging.getLogger(__name__)

class TavilyClient:
    def __init__(self):
        # List of env var names to check for keys
        self.key_vars = [
            "TAVILY_API_KEY",
            "TAVILY_PRIMARY_KEY",
            "TAVILY_SECONDARY_KEY", 
            "TAVILY_THIRD_KEY",
            "TAVILY_FOURTH_KEY",
            "TAVILY_FIFTH_KEY"
        ]
        self.available_keys = self._get_keys()
        if not self.available_keys:
            logger.warning("No Tavily API keys found in environment variables.")

    def _get_keys(self) -> List[str]:
        keys = []
        for var in self.key_vars:
            key = os.getenv(var)
            if key and key.strip():
                keys.append(key.strip())
        return keys

    def search_news(self, query: str) -> str:
        """
        Searches for news using Tavily with automatic failover across available keys.
        """
        if not self.available_keys:
            return "Error: No search API keys configured."

        for i, api_key in enumerate(self.available_keys):
            try:
                # Initialize client with current key
                client = BaseTavilyClient(api_key=api_key)
                
                # Perform search - specifically for news/finance context
                # "news" topic limits to news sources
                response = client.search(
                    query=query, 
                    topic="news", 
                    days=3, 
                    max_results=5,
                    include_domains=None, # Can specify valid finance domains here if needed
                    exclude_domains=None
                )
                
                # If successful, format and return
                return self._format_response(response)

            except Exception as e:
                logger.error(f"Tavily search failed with key {i+1} ({self.key_vars[i]}): {e}")
                # Continue to next key loop
                continue
        
        return "Sorry, I am currently unable to fetch the latest news due to service errors."

    def _format_response(self, response: Dict) -> str:
        results = response.get("results", [])
        if not results:
            return "No recent news found for this topic."

        formatted_output = "Here is the latest news:\n\n"
        for item in results:
            title = item.get("title", "No Title")
            url = item.get("url", "#")
            content = item.get("content", "No summary available.")
            formatted_output += f"**[{title}]({url})**\n{content}\n\n"
        
        return formatted_output.strip()

# Singleton instance
tavily_client = TavilyClient()
