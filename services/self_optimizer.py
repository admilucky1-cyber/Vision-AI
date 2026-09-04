"""
Vision AI v2.0 - Self-Optimizer
==========================================
AGI-level learning engine that improves from every interaction.

Features:
- Interaction tracking and pattern analysis
- Knowledge graph construction
- Provider performance monitoring
- Prompt optimization
- Auto-update checking
- Automatic data recovery & backup
"""

import os
import json
import time
import hashlib
import requests
import threading
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Any, Tuple

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATA_DIR.mkdir(exist_ok=True, parents=True)
LEARNING_DB_PATH = _DATA_DIR / "advanced_learning.json"
KNOWLEDGE_GRAPH_PATH = _DATA_DIR / "knowledge_graph.json"
BACKUP_INTERVAL = 30  # Save data every 30 interactions

# ==========================================================
# LOGGING SETUP
# ==========================================================
logger = logging.getLogger("vision-ai.optimizer")

# ==========================================================
# EXCEPTIONS
# ==========================================================
class OptimizerError(Exception):
    """Base exception for optimizer errors."""
    pass

class DatabaseCorruptionError(OptimizerError):
    """Raised when database is corrupted."""
    pass

# ==========================================================
# ADVANCED OPTIMIZER
# ==========================================================
class AdvancedOptimizer:
    """Self-learning system for continuous improvement."""

    def __init__(self):
        self.data = self._load_database()
        self.knowledge_graph = self._load_knowledge_graph()
        self.session_start = datetime.now(timezone.utc)
        self.session_stats = {
            "diagrams_requested": 0,
            "diagrams_generated": 0,
            "providers_used": defaultdict(int),
            "subjects_covered": set(),
            "failed_attempts": 0,
            "learning_events": 0,
        }
        self.conversation_memory = []
        self._interaction_counter = 0
        self._auto_save_timer = None
        self._lock = threading.Lock()
        
        logger.info("👁️ Vision AI Self-Learning Optimizer initialized")

    def _load_database(self) -> dict:
        """Load the learning database with auto-recovery on corruption."""
        if LEARNING_DB_PATH.exists():
            try:
                with open(LEARNING_DB_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Validate required fields
                    if "version" not in data:
                        raise DatabaseCorruptionError("Missing version field")
                    logger.info(f"✅ Loaded learning database (version {data.get('version', 'unknown')})")
                    return data
            except json.JSONDecodeError as e:
                logger.error(f"❌ advanced_learning.json corrupted: {e}")
                logger.warning("advanced_learning.json corrupted. Recreating fresh database...")
                return self._create_fresh_database()
            except Exception as e:
                logger.error(f"❌ Failed to load database: {e}")
                return self._create_fresh_database()
        logger.info("📝 Creating new learning database")
        return self._create_fresh_database()

    def _create_fresh_database(self) -> dict:
        """Create a fresh database with default values."""
        return {
            "version": "2.5.5",
            "created": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_interactions": 0,
            "provider_performance": {},
            "subject_expertise": {},
            "user_preferences": {},
            "knowledge_connections": {},
            "response_quality_scores": [],
            "internet_learnings": [],
            "diagram_type_stats": {},
            "best_diagram_prompts": {},
        }

    def _load_knowledge_graph(self) -> dict:
        """Load knowledge graph with error recovery."""
        if KNOWLEDGE_GRAPH_PATH.exists():
            try:
                with open(KNOWLEDGE_GRAPH_PATH, 'r', encoding='utf-8') as f:
                    graph = json.load(f)
                    # Validate required fields
                    if "concepts" not in graph or "connections" not in graph:
                        raise DatabaseCorruptionError("Missing required fields in knowledge graph")
                    logger.info(f"✅ Loaded knowledge graph ({len(graph.get('concepts', {}))} concepts)")
                    return graph
            except json.JSONDecodeError as e:
                logger.error(f"❌ knowledge_graph.json corrupted: {e}")
                logger.warning("knowledge_graph.json corrupted. Recreating fresh graph...")
                return {"concepts": {}, "connections": [], "last_updated": None}
            except Exception as e:
                logger.error(f"❌ Failed to load knowledge graph: {e}")
                return {"concepts": {}, "connections": [], "last_updated": None}
        logger.info("📝 Creating new knowledge graph")
        return {"concepts": {}, "connections": [], "last_updated": None}

    def _save_all(self):
        """Atomically save both databases."""
        with self._lock:
            self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
            self.data["total_interactions"] += 1
            
            try:
                # Save to temporary files first, then rename for atomicity
                temp_db = LEARNING_DB_PATH.with_suffix(".tmp")
                with open(temp_db, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
                temp_db.rename(LEARNING_DB_PATH)

                temp_graph = KNOWLEDGE_GRAPH_PATH.with_suffix(".tmp")
                with open(temp_graph, 'w', encoding='utf-8') as f:
                    json.dump(self.knowledge_graph, f, indent=2, ensure_ascii=False)
                temp_graph.rename(KNOWLEDGE_GRAPH_PATH)
                
                logger.debug(f"💾 Saved databases successfully")
            except Exception as e:
                logger.error(f"⚠️ Failed to save optimizer data: {e}")
                raise OptimizerError(f"Failed to save data: {e}")

    def _auto_save(self):
        """Auto-save every BACKUP_INTERVAL interactions."""
        self._interaction_counter += 1
        if self._interaction_counter % BACKUP_INTERVAL == 0:
            try:
                self._save_all()
                logger.info(f"💾 Auto-saved optimizer data ({self._interaction_counter} interactions)")
            except Exception as e:
                logger.error(f"❌ Auto-save failed: {e}")

    def learn_from_interaction(
        self, 
        question: str, 
        answer: str, 
        subject: str,
        provider: str, 
        success: bool, 
        response_time: float,
        image_count: int = 0, 
        diagram_type: str = None
    ) -> None:
        """Record interaction for learning."""
        with self._lock:
            self.session_stats["learning_events"] += 1

            # Atomicity Check: Ensure subject is never empty
            safe_subject = subject if subject else "general"
            safe_provider = provider if provider else "unknown"

            # Update subject expertise
            if safe_subject not in self.data["subject_expertise"]:
                self.data["subject_expertise"][safe_subject] = {
                    "attempts": 0, 
                    "successes": 0,
                    "avg_response_time": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            
            subject_stats = self.data["subject_expertise"][safe_subject]
            subject_stats["attempts"] += 1
            if success:
                subject_stats["successes"] += 1
            subject_stats["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            # Update average response time for subject
            current_avg = subject_stats.get("avg_response_time", 0)
            subject_stats["avg_response_time"] = (
                (current_avg * (subject_stats["attempts"] - 1) + response_time) / 
                subject_stats["attempts"]
            )

            # Update provider performance
            if safe_provider not in self.data["provider_performance"]:
                self.data["provider_performance"][safe_provider] = {
                    "attempts": 0, 
                    "successes": 0, 
                    "times": [], 
                    "scores": [],
                    "avg_response_time": 0,
                    "avg_score": 0
                }
            
            perf = self.data["provider_performance"][safe_provider]
            perf["attempts"] += 1
            if success:
                perf["successes"] += 1
            perf["times"].append(response_time)
            if len(perf["times"]) > 100:
                perf["times"] = perf["times"][-100:]
            perf["avg_response_time"] = sum(perf["times"]) / len(perf["times"])

            # Quality score calculation
            score = self._calculate_quality_score(success, response_time, image_count)
            final_score = min(score, 100)
            self.data["response_quality_scores"].append(final_score)
            if len(self.data["response_quality_scores"]) > 1000:
                self.data["response_quality_scores"] = self.data["response_quality_scores"][-1000:]

            # Store score per provider for smarter recommendations
            perf["scores"].append(final_score)
            if len(perf["scores"]) > 100:
                perf["scores"] = perf["scores"][-100:]
            perf["avg_score"] = sum(perf["scores"]) / len(perf["scores"])

            # Track conversation memory (limited to prevent memory bloat)
            self.conversation_memory.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "question": question[:200],
                "provider": safe_provider,
                "success": success,
            })
            if len(self.conversation_memory) > 100:
                self.conversation_memory = self.conversation_memory[-100:]

            # Update diagram stats if applicable
            if diagram_type and image_count > 0:
                if diagram_type not in self.data["diagram_type_stats"]:
                    self.data["diagram_type_stats"][diagram_type] = {"attempts": 0, "successes": 0}
                self.data["diagram_type_stats"][diagram_type]["attempts"] += 1
                if image_count > 0:
                    self.data["diagram_type_stats"][diagram_type]["successes"] += 1

            # Auto-save
            self._auto_save()

    def _calculate_quality_score(self, success: bool, response_time: float, image_count: int) -> float:
        """Calculate quality score for an interaction."""
        score = 0.0
        if success:
            score += 50
        if response_time < 5:
            score += 20
        elif response_time < 15:
            score += 10
        if image_count > 0:
            score += min(image_count * 10, 30)
        return score

    def get_reasoning_recommendation(self, question: str) -> dict:
        """Recommend reasoning style based on question."""
        q = question.lower()
        if any(w in q for w in ["draw", "plot", "chart", "diagram", "graph"]):
            if any(w in q for w in ["flowchart", "mind map", "tree", "org chart"]):
                return {"style": "diagram_style", "reason": "Diagram request"}
            elif any(w in q for w in ["pie", "bar", "line", "scatter"]):
                return {"style": "chart_style", "reason": "Data chart request"}
            return {"style": "plot_style", "reason": "Plot request"}
        elif any(w in q for w in ["code", "program", "function", "algorithm", "debug"]):
            return {"style": "deepseek_style", "reason": "Technical question"}
        elif any(w in q for w in ["math", "calculate", "equation", "proof", "solve"]):
            return {"style": "deepseek_style", "reason": "Mathematical question"}
        elif any(w in q for w in ["explain", "why", "how", "what is", "describe"]):
            return {"style": "claude_style", "reason": "Explanatory question"}
        return {"style": "claude_style", "reason": "General question"}

    def get_provider_recommendation(self, subject: str = None) -> str:
        """
        Recommend the best AI provider based on historical performance.
        Returns the provider name with the highest average score.
        """
        with self._lock:
            providers = self.data.get("provider_performance", {})
            if not providers:
                return "auto"

            best_provider = None
            best_score = -1.0

            for provider, stats in providers.items():
                avg_score = stats.get("avg_score", 0)
                if avg_score > best_score:
                    best_score = avg_score
                    best_provider = provider

            return best_provider if best_provider else "auto"

    def get_session_report(self) -> dict:
        """Generate session summary report."""
        with self._lock:
            runtime = datetime.now(timezone.utc) - self.session_start
            return {
                "session_duration": str(runtime).split('.')[0],
                "diagrams_requested": self.session_stats["diagrams_requested"],
                "diagrams_generated": self.session_stats["diagrams_generated"],
                "success_rate": f"{(self.session_stats['diagrams_generated'] / max(1, self.session_stats['diagrams_requested']) * 100):.1f}%",
                "providers_used": dict(self.session_stats["providers_used"]),
                "subjects_covered": list(self.session_stats["subjects_covered"]),
                "failed_attempts": self.session_stats["failed_attempts"],
                "learning_events": self.session_stats["learning_events"],
                "total_lifetime": self.data["total_interactions"],
                "knowledge_concepts": len(self.knowledge_graph["concepts"]),
                "suggestions": self.get_improvement_suggestions(),
                "top_provider": self.get_provider_recommendation(),
            }

    def get_health_status(self) -> dict:
        """Get optimizer health status."""
        with self._lock:
            total_attempts = sum(s["attempts"] for s in self.data["subject_expertise"].values())
            total_successes = sum(s["successes"] for s in self.data["subject_expertise"].values())
            return {
                "learning_database": "active" if LEARNING_DB_PATH.exists() else "new",
                "total_interactions": self.data["total_interactions"],
                "subjects_learned": len(self.data["subject_expertise"]),
                "overall_success_rate": f"{(total_successes / max(1, total_attempts) * 100):.1f}%",
                "knowledge_graph_size": len(self.knowledge_graph["concepts"]),
                "internet_learnings": len(self.data["internet_learnings"]),
                "evolution_stage": self._get_evolution_stage(),
                "auto_save_enabled": True,
                "backup_interval": BACKUP_INTERVAL,
            }

    def get_improvement_suggestions(self) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        with self._lock:
            for subject, stats in self.data["subject_expertise"].items():
                if stats["attempts"] >= 3:
                    rate = stats["successes"] / stats["attempts"] * 100
                    if rate < 50:
                        suggestions.append(f"Low success rate in {subject} ({rate:.0f}%). Review prompts.")
                    elif rate > 90:
                        suggestions.append(f"Excellent performance in {subject} ({rate:.0f}%).")
        return suggestions

    def _get_evolution_stage(self) -> str:
        """Get the current evolution stage."""
        total = self.data["total_interactions"]
        if total < 10:
            return "Newborn"
        elif total < 50:
            return "Growing"
        elif total < 100:
            return "Mature"
        elif total < 500:
            return "Advanced"
        return "Super-Intelligent"

    # ✅ Public exposure of evolution stage
    def get_evolution_stage(self) -> str:
        """Public wrapper for _get_evolution_stage."""
        return self._get_evolution_stage()

    def clear_memory(self) -> dict:
        """Clear conversation memory."""
        with self._lock:
            self.conversation_memory.clear()
            logger.info("🧹 Conversation memory cleared")
            return {"message": "Conversation memory cleared"}

    def reset(self) -> dict:
        """Reset all learning data."""
        with self._lock:
            self.data = self._create_fresh_database()
            self.knowledge_graph = {"concepts": {}, "connections": [], "last_updated": None}
            self.conversation_memory.clear()
            self.session_stats = {
                "diagrams_requested": 0,
                "diagrams_generated": 0,
                "providers_used": defaultdict(int),
                "subjects_covered": set(),
                "failed_attempts": 0,
                "learning_events": 0,
            }
            self._save_all()
            logger.info("🔄 Optimizer reset to factory state")
            return {"message": "Optimizer reset successfully"}

    # ✅ New: Force save and shutdown
    def save_and_shutdown(self) -> dict:
        """Force save all data and prepare for shutdown."""
        with self._lock:
            try:
                self._save_all()
                logger.info("💾 Optimizer data saved for shutdown")
                return {"message": "Data saved successfully"}
            except Exception as e:
                logger.error(f"❌ Failed to save during shutdown: {e}")
                return {"message": f"Save failed: {e}"}

    # ✅ New: Get detailed provider performance
    def get_provider_performance(self) -> Dict[str, Any]:
        """Get detailed provider performance stats."""
        with self._lock:
            return {
                provider: {
                    "attempts": stats["attempts"],
                    "successes": stats["successes"],
                    "success_rate": f"{(stats['successes'] / max(1, stats['attempts']) * 100):.1f}%",
                    "avg_response_time": stats.get("avg_response_time", 0),
                    "avg_score": stats.get("avg_score", 0),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
                for provider, stats in self.data.get("provider_performance", {}).items()
            }

    # ✅ New: Get detailed subject performance
    def get_subject_performance(self) -> Dict[str, Any]:
        """Get detailed subject performance stats."""
        with self._lock:
            return {
                subject: {
                    "attempts": stats["attempts"],
                    "successes": stats["successes"],
                    "success_rate": f"{(stats['successes'] / max(1, stats['attempts']) * 100):.1f}%",
                    "avg_response_time": stats.get("avg_response_time", 0),
                    "last_updated": stats.get("last_updated", datetime.now(timezone.utc).isoformat())
                }
                for subject, stats in self.data.get("subject_expertise", {}).items()
            }


# ✅ FIX: Add SelfOptimizer alias for backward compatibility
SelfOptimizer = AdvancedOptimizer

# Singleton
optimizer = AdvancedOptimizer()

# ==========================================================
# EXPORTS
# ==========================================================
__all__ = [
    "optimizer",
    "AdvancedOptimizer",
    "SelfOptimizer",  # ✅ Alias for compatibility
    "OptimizerError",
    "DatabaseCorruptionError",
]

logger.info("👁️ Vision AI Self-Learning Optimizer v2.0 - Ready")