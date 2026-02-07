import os
import logging
import httpx
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class TavilyClient:
    """
    Tavily News Search Client using direct API calls (no library dependency).
    Implements automatic failover across multiple API keys.
    """
    
    def __init__(self):
        self.api_url = "https://api.tavily.com/search"
        
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
            logger.warning("⚠️ No Tavily API keys found in environment variables.")
        else:
            logger.info(f"✅ Tavily client initialized with {len(self.available_keys)} API key(s)")

    def _get_keys(self) -> List[str]:
        """Extract and validate API keys from environment variables."""
        keys = []
        for var in self.key_vars:
            key = os.getenv(var)
            if key and key.strip():
                # Remove quotes if present
                clean_key = key.strip().strip('"').strip("'")
                keys.append(clean_key)
        return keys

    async def search_news(self, query: str) -> str:
        """
        Searches for news using Tavily API with automatic failover.
        
        Args:
            query: Search query (e.g., "HDFC Bank", "Reliance stock")
            
        Returns:
            Formatted news results or error message
        """
        if not self.available_keys:
            return "Error: No search API keys configured."

        for i, api_key in enumerate(self.available_keys):
            try:
                # Prepare request payload
                payload = {
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "basic",  # or "advanced" for more results
                    "topic": "news",  # Focus on news sources
                    "days": 3,  # Last 3 days
                    "max_results": 5,
                    "include_answer": False,  # We don't need AI summary
                    "include_raw_content": False,  # Save bandwidth
                    "include_images": False
                }
                
                # Make API request
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.api_url,
                        json=payload,
                        timeout=10.0
                    )
                    
                    # Check response status
                    if response.status_code == 200:
                        data = response.json()
                        return self._format_response(data)
                    elif response.status_code == 401:
                        logger.warning(f"Invalid API key {i+1}, trying next...")
                        continue
                    elif response.status_code == 429:
                        logger.warning(f"Rate limit hit on key {i+1}, trying next...")
                        continue
                    else:
                        logger.error(f"Tavily API error {response.status_code}: {response.text}")
                        continue

            except httpx.TimeoutException:
                logger.error(f"Tavily search timeout with key {i+1}")
                continue
            except Exception as e:
                logger.error(f"Tavily search failed with key {i+1}: {type(e).__name__}: {e}")
                continue
        
        return "Sorry, I am currently unable to fetch the latest news due to service errors."

    def _format_response(self, data: Dict) -> str:
        """Format Tavily API response into readable text."""
        results = data.get("results", [])
        
        if not results:
            return "No recent news found for this topic."

        formatted_output = "Here is the latest news:\n\n"
        for item in results:
            title = item.get("title", "No Title")
            url = item.get("url", "#")
            content = item.get("content", "No summary available.")
            published_date = item.get("published_date", "")
            
            # Add date if available
            date_str = f" ({published_date})" if published_date else ""
            
            formatted_output += f"**[{title}]({url})**{date_str}\n{content}\n\n"
        
        return formatted_output.strip()

# Singleton instance
tavily_client = TavilyClient()
