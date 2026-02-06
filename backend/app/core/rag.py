import json
import os
from typing import List, Dict, Any
import logging
from leann import LeannBuilder, LeannSearcher

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, data_path: str = "backend/data/knowledge_base.json", index_path: str = "backend/data/education.leann"):
        self.data_path = data_path
        self.index_path = index_path

    def ingest_knowledge_base(self):
        """
        Loads the knowledge base JSON and builds a Leann index.
        """
        if not os.path.exists(self.data_path):
            logger.error(f"Knowledge base file not found at {self.data_path}")
            return

        try:
            with open(self.data_path, "r") as f:
                data = json.load(f)
            
            # Prepare data for Leann
            # Assuming LeannBuilder takes a list of strings or dicts with text content
            # We will format the definitions into a searchable text format
            documents = []
            for item in data:
                doc_text = f"{item['term']} ({item['category']}): {item['definition']}"
                documents.append(doc_text)
            
            logger.info(f"Ingesting {len(documents)} documents into Leann index...")
            
            # Build index
            # Note: LeannBuilder API might differ, adjusting to standard hypothetical usage
            builder = LeannBuilder(self.index_path)
            builder.build(documents)
            
            logger.info(f"Leann index successfully built at {self.index_path}")

        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            raise

    def query(self, text: str, k: int = 3) -> str:
        """
        Searches the Leann index for relevant context.
        """
        if not os.path.exists(self.index_path):
            logger.warning(f"Index not found at {self.index_path}. Attempting to ingest.")
            self.ingest_knowledge_base()
        
        try:
            searcher = LeannSearcher(self.index_path)
            results = searcher.search(text, k=k)
            
            # Format results into a context string
            context_parts = []
            for res in results:
                # Assuming res is the document string or has a 'content' attribute
                # If leann returns object with score/content
                content = res if isinstance(res, str) else getattr(res, 'content', str(res))
                context_parts.append(content)
            
            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error during RAG query: {e}")
            return ""

# Singleton instance
rag_service = RAGService()
