from app.routers.scenarios import router as scenarios_router
from app.routers.words import router as words_router
from app.routers.learning import router as learning_router
from app.routers.auth import router as auth_router
from app.routers.speech import router as speech_router

__all__ = ["scenarios_router", "words_router", "learning_router", "auth_router", "speech_router"]
