"""
Vision AI v2.0 - Services Package
=================================
Core AI services including LLM, multimodal processing, search, and image generation.
"""

import logging

logger = logging.getLogger("vision-ai.services")

__version__ = "2.5.5"

# Correctly import the core logic functions
from .llm import ask_ai, detect_subject, list_available_models
from .multimodal import process_uploaded_file  
from .search import search_web, is_search_needed, auto_search_context, get_current_info
from .self_optimizer import optimizer, SelfOptimizer
from .image_gen import generate_all_diagrams, generate_diagram, generate_chart
from .youtube import get_video_info, get_video_transcript, get_video_context, extract_video_id, download_video, get_direct_media_urls

# ==========================================================
# PUBLIC API (Ensures `services.optimizer` works)
# ==========================================================
__all__ = [
    "ask_ai",
    "detect_subject",
    "list_available_models",
    "process_uploaded_file", 
    "search_web",
    "is_search_needed",
    "auto_search_context",
    "get_current_info",
    "optimizer",
    "SelfOptimizer",
    "generate_all_diagrams",
    "generate_diagram",
    "generate_chart",
    "get_video_info",
    "get_video_transcript",
    "get_video_context",
    "extract_video_id",
    "download_video",
]

logger.info(f"👁️ Vision AI Services v{__version__} - Ready")
# v2.7.0 rag re-ranker
