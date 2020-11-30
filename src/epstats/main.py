import logging
from concurrent.futures import ThreadPoolExecutor
from statsd import StatsClient
from pydantic import BaseSettings

from .toolkit.testing import TestDaoFactory, TestData
from .server import get_api, serve, ApiSettings


class Settings(BaseSettings):
    api: ApiSettings = ApiSettings()

    statsd_host: str = "localhost"
    statsd_port: int = 8888

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


def get_statsd():
    try:
        prefix = f"{settings.api.app_name}.{settings.api.app_env}"
        statsd = StatsClient(settings.statsd_host, settings.statsd_port, prefix=prefix)
        yield statsd
    finally:
        pass


api = get_api(settings.api, get_dao, get_executor_pool, get_statsd)


def main():
    from .config import config

    logging.config.dictConfig(config["logging"])
    serve("epstats:api", settings.api, config["logging"])


if __name__ == "__main__":
    main()
