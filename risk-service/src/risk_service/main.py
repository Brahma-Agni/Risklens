import logging

import uvicorn

from risk_service.api import create_app
from risk_service.config import get_settings

settings = get_settings()
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
app = create_app(settings=settings)


def run() -> None:
    uvicorn.run(
        "risk_service.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
