import uvicorn
from core.config import settings
from core.logging import setup_logging

setup_logging()

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )
