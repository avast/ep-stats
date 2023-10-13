import logging
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseSettings

from .toolkit.testing import TestDaoFactory, TestData
from .server import get_api, serve, ApiSettings
from prometheus_client import make_asgi_app, multiprocess, CollectorRegistry


class Settings(BaseSettings):
    api: ApiSettings = ApiSettings()

    evaluation_pool_size: int = 5


settings = Settings()


def get_dao_factory():
    return TestDaoFactory(TestData())


def get_dao():
    try:
        dao = get_dao_factory().get_dao()
        yield dao
    finally:
        dao.close()


def get_executor_pool():
    try:
        evaluation_pool_size = settings.evaluation_pool_size
        evaluation_pool = ThreadPoolExecutor(max_workers=evaluation_pool_size)
        yield evaluation_pool
    finally:
        pass


def make_metrics_app():
    if settings.api.web_workers == 1:
        return make_asgi_app()
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    return make_asgi_app(registry=registry)


api = get_api(settings.api, get_dao, get_executor_pool)
metrics_app = make_metrics_app()
api.mount("/metrics", metrics_app)


def main():
    from .config import config

    logging.config.dictConfig(config["logging"])
    serve("epstats:api", settings.api, config["logging"])


if __name__ == "__main__":
    main()
