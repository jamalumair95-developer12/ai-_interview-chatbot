"""Chroma vector store and retriever for resume RAG."""

import gc
import logging
import os
import shutil
import threading
import time
import weakref
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from utils.embeddings import get_embeddings
from utils.helpers import PROJECT_ROOT
from utils.text_splitter import split_resume_text

logger = logging.getLogger(__name__)

# Prevent concurrent index/clear (e.g. double-clicks) from corrupting SQLite.
_index_lock = threading.Lock()


def get_chroma_persist_dir() -> Path:
    rel = os.getenv("CHROMA_PERSIST_DIR", "vector_db/chroma_db")
    path = (PROJECT_ROOT / rel).resolve()
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o755)
    return path


def get_chroma_client_settings() -> ChromaSettings:
    """Local dev settings: allow reset when re-indexing a resume."""
    return ChromaSettings(
        allow_reset=True,
        anonymized_telemetry=False,
        is_persistent=True,
    )


class ResumeVectorStore:
    """Manage Chroma persistence for a single resume collection."""

    _instances: weakref.WeakSet["ResumeVectorStore"] = weakref.WeakSet()

    def __init__(self, collection_name: str = "resume_collection"):
        self.collection_name = collection_name
        self.persist_dir = get_chroma_persist_dir()
        self._vectorstore: Optional[Chroma] = None
        ResumeVectorStore._instances.add(self)

    @classmethod
    def _close_all_instances(cls) -> None:
        """Close every live store so SQLite releases the persist directory."""
        for store in list(cls._instances):
            store._close_vectorstore()

    def _close_vectorstore(self) -> None:
        """Release Chroma client handles before re-indexing."""
        if self._vectorstore is None:
            return
        try:
            client = getattr(self._vectorstore, "_client", None)
            if client is not None:
                try:
                    client.delete_collection(self.collection_name)
                except Exception:
                    pass
        except Exception as exc:
            logger.warning("Chroma collection close failed: %s", exc)
        finally:
            self._vectorstore = None

    def _clear_persist_dir(self) -> None:
        """Remove persisted vectors (caller must hold _index_lock)."""
        ResumeVectorStore._close_all_instances()
        gc.collect()
        time.sleep(0.1)

        if not self.persist_dir.exists():
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(self.persist_dir, 0o755)
            return

        try:
            client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=get_chroma_client_settings(),
            )
            client.reset()
        except Exception as exc:
            logger.warning("Chroma reset failed, removing persist dir: %s", exc)
            for attempt in range(3):
                try:
                    shutil.rmtree(self.persist_dir)
                    break
                except OSError as rm_exc:
                    if attempt == 2:
                        raise rm_exc from exc
                    time.sleep(0.2)

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.persist_dir, 0o755)
        logger.info("Cleared vector store at %s", self.persist_dir)

    def clear(self) -> None:
        """Remove persisted vectors for a fresh upload."""
        with _index_lock:
            self._clear_persist_dir()

    def build_from_text(self, resume_text: str, metadata: Optional[dict] = None) -> Chroma:
        """Chunk resume, embed, and persist to Chroma."""
        with _index_lock:
            self._clear_persist_dir()
            chunks = split_resume_text(resume_text)
            meta = metadata or {}
            documents = [
                Document(page_content=chunk, metadata={**meta, "chunk_index": i})
                for i, chunk in enumerate(chunks)
            ]
            embeddings = get_embeddings()
            self._vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                collection_name=self.collection_name,
                persist_directory=str(self.persist_dir),
                client_settings=get_chroma_client_settings(),
            )
            logger.info("Built Chroma index with %d documents.", len(documents))
            return self._vectorstore

    def load(self) -> Optional[Chroma]:
        """Load existing Chroma store from disk."""
        if not any(self.persist_dir.iterdir()):
            return None
        embeddings = get_embeddings()
        self._vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=embeddings,
            persist_directory=str(self.persist_dir),
            client_settings=get_chroma_client_settings(),
        )
        return self._vectorstore

    def get_retriever(self, k: int = 4):
        """Return a LangChain retriever over resume chunks."""
        if self._vectorstore is None:
            self.load()
        if self._vectorstore is None:
            raise RuntimeError("No resume indexed. Please upload a resume first.")
        return self._vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k},
        )

    def get_relevant_context(self, query: str, k: int = 4) -> str:
        """Fetch top-k chunks as a single context string."""
        retriever = self.get_retriever(k=k)
        docs = retriever.invoke(query)
        return "\n\n---\n\n".join(d.page_content for d in docs)
