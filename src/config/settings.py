import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class AppSettings(BaseSettings):
    """Central configuration class for Enterprise GenAI Strategy Engine."""
    
    # Base paths
    base_dir: Path = BASE_DIR
    upload_dir: Path = BASE_DIR / "data" / "uploaded"
    metadata_dir: Path = BASE_DIR / "data" / "metadata"
    cache_dir: Path = BASE_DIR / "data" / "cache"
    sample_data_dir: Path = BASE_DIR / "data" / "sample_documents"
    
    # Application Mode
    app_env: str = "development"
    log_level: str = "INFO"
    
    # LLM Configuration
    llm_provider: str = Field(default="ollama", description="ollama, openai, groq, or mock")
    llm_model: str = "llama3:latest"
    llm_base_url: str = "http://localhost:11434"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048
    
    # Cloud API Keys
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Embeddings
    embedding_provider: str = "sentence-transformers"
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    
    # ChromaDB
    chroma_persist_directory: str = str(BASE_DIR / "chroma_db")
    chroma_collection_name: str = "enterprise_rag_knowledge"
    
    # Hybrid Retrieval Settings
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    rrf_k: int = 60
    default_top_k: int = 5
    reranker_enabled: bool = False
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Chunking Defaults
    default_chunk_size: int = 800
    default_chunk_overlap: int = 150
    parent_chunk_size: int = 2000
    parent_chunk_overlap: int = 200

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def ensure_directories(self) -> None:
        """Create storage directories if they do not exist."""
        for path in [self.upload_dir, self.metadata_dir, self.cache_dir, self.sample_data_dir, Path(self.chroma_persist_directory)]:
            path.mkdir(parents=True, exist_ok=True)


_settings_instance: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """Retrieve cached global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = AppSettings()
        _settings_instance.ensure_directories()
    return _settings_instance
