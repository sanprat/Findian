import json
import os
import httpx
from typing import List, Dict, Any
import logging
import chromadb

logger = logging.getLogger(__name__)

CHUTES_EMBEDDING_URL = (
    "https://chutes-qwen-qwen3-embedding-0-6b.chutes.ai/v1/embeddings"
)


class RAGService:
    def __init__(
        self,
        data_path: str = None,
        persist_dir: str = None,
    ):
        # Determine paths that work both locally and in Docker
        # In Docker, files are at /app/data/...
        # Locally, files are at backend/data/...
        
        if data_path is None:
            if os.path.exists("data/knowledge_base.json"):
                self.data_path = "data/knowledge_base.json"
            else:
                self.data_path = "backend/data/knowledge_base.json"
        else:
            self.data_path = data_path
            
        if persist_dir is None:
            if os.path.exists("data"):
                self.persist_dir = "data/chroma_db"
            else:
                self.persist_dir = "backend/data/chroma_db"
        else:
            self.persist_dir = persist_dir

        self.collection_name = "stock_knowledge"
        self.api_token = os.getenv("CHUTES_API_TOKEN")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        os.makedirs(self.persist_dir, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Stock market education knowledge base"},
        )
        logger.info("ChromaDB initialized with Chutes embeddings")

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not self.api_token:
            logger.error("CHUTES_API_TOKEN not set")
            return [[0.0] * 768 for _ in texts]

        payload = {"input": texts}

        response = httpx.post(
            CHUTES_EMBEDDING_URL,
            headers={"Authorization": f"Bearer {self.api_token}"},
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    def ingest_knowledge_base(self):
        if not os.path.exists(self.data_path):
            logger.error(f"Knowledge base file not found at {self.data_path}")
            return

        try:
            with open(self.data_path, "r") as f:
                data = json.load(f)

            documents = []
            ids = []
            metadatas = []

            for i, item in enumerate(data):
                doc_text = f"{item['term']} ({item['category']}): {item['definition']}"
                documents.append(doc_text)
                ids.append(f"doc_{i}")
                metadatas.append({"term": item["term"], "category": item["category"]})

            logger.info(f"Ingesting {len(documents)} documents into ChromaDB...")

            embeddings = self._get_embeddings(documents)

            self.collection.add(
                documents=documents, ids=ids, metadatas=metadatas, embeddings=embeddings
            )

            logger.info(f"Successfully indexed {len(documents)} documents in ChromaDB")

        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            raise

    def query(self, text: str, k: int = 3) -> str:
        try:
            query_embedding = self._get_embeddings([text])

            results = self.collection.query(
                query_embeddings=query_embedding, n_results=k
            )

            if not results["documents"][0]:
                return ""

            return "\n\n".join(results["documents"][0])

        except Exception as e:
            logger.error(f"Error during RAG query: {e}")
            return ""


rag_service = RAGService()
