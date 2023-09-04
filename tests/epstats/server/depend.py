from concurrent.futures import ThreadPoolExecutor

from src.epstats.toolkit.testing import TestDaoFactory, TestData

dao_factory = TestDaoFactory(TestData())


def get_test_dao():
    dao = dao_factory.get_dao()
    try:
        yield dao
    finally:
        dao.close()


def get_test_executor_pool():
    evaluation_pool = ThreadPoolExecutor(max_workers=1)
    try:
        yield evaluation_pool
    finally:
        pass
