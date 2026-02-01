"""Application state management."""
import time


class AppState:
    """Application state container."""

    def __init__(self) -> None:
        self.db_engine = None
        self.redis_client = None
        self.opensearch_client = None
        self.start_time = time.time()


# Global application state instance
app_state = AppState()
