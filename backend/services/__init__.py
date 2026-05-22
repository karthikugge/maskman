"""
backend/services/__init__.py

Public surface of the services package.
Lazy imports to avoid crashing on missing heavy dependencies
(like sentence-transformers) that aren't needed for the chatbot.
"""

# Import only the lightweight chatbot agent eagerly
from backend.services.ai_agent import chatbot_agent

# Heavy ML/embedding modules are imported lazily to avoid
# crashing the server if sentence-transformers is not installed.
def _lazy_import_ml():
    from backend.services.embeddings import EmbeddingsService, embeddings_service
    from backend.services.ml_models import (
        PriceIntelligenceAgent, DealDetectionAgent, AnomalyDetectionAgent,
        PriceForecast, DealAnalysis, AnomalyResult,
    )
    from backend.services.agents import (
        ProductUnderstandingAgent, MatchingAgent, RecommendationAgent,
        SimilarProduct, RecommendationResult, AgentError,
    )

__all__ = [
    "chatbot_agent",
]