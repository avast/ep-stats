import logging
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..prometheus import get_prometheus_metric, Summary, Counter
from ..toolkit import Experiment as EvExperiment
from ..toolkit import Dao

from .req import Experiment
from .res import Result


_logger = logging.getLogger("epstats")
evaluation_duration_metric = get_prometheus_metric(
    "evaluation_duration_seconds", Summary, ["exp_id", "is_performance_test"]
)
query_duration_metric = get_prometheus_metric("query_duration_seconds", Summary, ["exp_id", "is_performance_test"])
stats_computation_duration_metric = get_prometheus_metric(
    "stats_computation_duration_seconds", Summary, ["exp_id", "is_performance_test"]
)
evaluation_errors_metric = get_prometheus_metric("evaluation_errors_total", Counter)
evaluation_successes_metric = get_prometheus_metric("evaluation_successes_total", Counter)
evaluation_requests_metric = get_prometheus_metric("evaluation_requests_total", Counter)


def get_evaluate_router(get_dao, get_executor_pool) -> APIRouter:
    def _evaluate(experiment: EvExperiment, dao: Dao):
        try:
            is_performance_test = experiment.query_parameters.get("is_performance_test") is True
            with evaluation_duration_metric.labels(experiment.id, is_performance_test).time():
                _logger.debug(f"Loading goals for experiment [{experiment.id}]")
                with query_duration_metric.labels(experiment.id, is_performance_test).time():
                    goals = dao.get_agg_goals(experiment).sort_values(["exp_variant_id", "goal"])
                    _logger.info(f"Retrieved {len(goals)} goals in experiment [{experiment.id}]")
                with stats_computation_duration_metric.labels(experiment.id, is_performance_test).time():
                    evaluation = experiment.evaluate_agg(goals)
                    evaluation_successes_metric.inc()
                _logger.info(
                    f"Evaluation response: [{experiment.id}]",
                    {
                        "metrics": (
                            evaluation.metrics.replace([np.inf, -np.inf], "inf")
                            .replace(np.nan, None)
                            .to_dict("records"),
                        )
                    },
                )
            return Result.from_evaluation(experiment, evaluation)
        except Exception as e:
            _logger.error(f"Cannot evaluate experiment [{experiment.id}] because of {e}")
            _logger.exception(e)
            evaluation_errors_metric.inc()
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
    ):
        """
        Evaluates single `Experiment`.
        """
        _logger.info(f"Evaluation request: [{experiment.id}]", experiment.dict())
        evaluation_requests_metric.inc()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(evaluation_pool, _evaluate, experiment.to_experiment(), dao)

    return router
