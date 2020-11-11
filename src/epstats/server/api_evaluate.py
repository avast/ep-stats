import logging
from fastapi import APIRouter, Depends, HTTPException
from statsd import StatsClient
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..toolkit import Experiment as EvExperiment
from ..toolkit import Dao

from .req import Experiment
from .res import Result


_logger = logging.getLogger("epstats")


def get_evaluate_router(get_dao, get_executor_pool, get_statsd) -> APIRouter:
    def _evaluate(experiment: EvExperiment, dao: Dao, statsd: StatsClient):
        try:
            with statsd.timer("timing.evaluation"):
                _logger.info(f"Evaluating experiment [{experiment.id}]")
                _logger.debug(f"Loading goals for experiment [{experiment.id}]")
                with statsd.timer("timing.query"):
                    goals = dao.get_agg_goals(experiment).sort_values(["exp_variant_id", "goal"])
                    _logger.info(f"Retrieved {len(goals)} goals in experiment [{experiment.id}]")
                with statsd.timer("timing.stats"):
                    evaluation = experiment.evaluate_agg(goals)
                    statsd.incr("evaluations")
                _logger.info(
                    (
                        f"Evaluation of experiment [{experiment.id}] finished with evaluation"
                        f" of {evaluation.metrics.metric_id.nunique()} "
                        f"metrics and {evaluation.checks.check_id.nunique()} checks"
                    )
                )
            return Result.from_evaluation(experiment, evaluation)
        except Exception as e:
            _logger.error(f"Cannot evaluate experiment [{experiment.id}] because of {e}")
            _logger.exception(e)
            statsd.incr("errors.experiment")
            raise HTTPException(
                status_code=500,
                detail=f"Cannot evaluate experiment [{experiment.id}] because of {e}",
            )

    router = APIRouter()

    @router.post("/evaluate", response_model=Result, tags=["Experiment Evaluation"])
    async def evaluate_experiment(
        experiment: Experiment,
        evaluation_pool: ThreadPoolExecutor = Depends(get_executor_pool),
        dao: Dao = Depends(get_dao),
        statsd: StatsClient = Depends(get_statsd),
    ):
        """
        Evaluates single `Experiment`.
        """
        _logger.info(f"Calling evaluate with {experiment.json()}")
        statsd.incr("requests.evaluate")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(evaluation_pool, _evaluate, experiment.to_experiment(statsd), dao, statsd)

    return router
