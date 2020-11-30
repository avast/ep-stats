import logging
from typing import Dict
import uvicorn
from statsd import StatsClient
from fastapi import FastAPI, Depends
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api_evaluate import get_evaluate_router
from .json_response import DataScienceJsonResponse
from .api_settings import ApiSettings


def get_api(settings: ApiSettings, get_dao, get_executor_pool, get_statsd) -> FastAPI:
    api = FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version="0.2.1",
        default_response_class=DataScienceJsonResponse,
    )

    @api.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request, exc):
        """
        We override default exception handler to send exception to the log.
        """
        logger = logging.getLogger("epstats")
        logger.error(f"HttpException status code [{exc.status_code}] detail [{exc.detail}]")
        return await http_exception_handler(request, exc)

    @api.exception_handler(RequestValidationError)
    async def custom_request_validation_exception_handler(request, exc):
        """
        We override default exception handler to send exception to the log.
        """
        logger = logging.getLogger("epstats")
        logger.exception(f"RequestValidationError: [{exc}], [{exc.body}]")
        return await request_validation_exception_handler(request, exc)

    @api.get("/health", tags=["Health"])
    async def readiness_liveness_probe(statsd: StatsClient = Depends(get_statsd)):
        statsd.incr("requests.health")
        return {"message": "ep-stats-api is ready"}

    api.include_router(get_evaluate_router(get_dao, get_executor_pool, get_statsd))

    return api


def serve(api: str, settings: ApiSettings, log_config: Dict):
    logger = logging.getLogger("epstats")
    logger.info(f"Starting {settings.app_name} in env {settings.app_env}")
    logger.info(f"Listening on http://{settings.host}:{settings.port}")
    logger.info(f"Starting with log level {settings.log_level}")
    logger.info(f"Using {settings.web_workers} web server worker threads")
    uvicorn.run(
        api,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        workers=settings.web_workers,
        timeout_keep_alive=0,
        log_config=log_config,
        http="h11",
    )
