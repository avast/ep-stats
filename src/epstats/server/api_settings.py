from pydantic import BaseSettings


class ApiSettings(BaseSettings):
    app_name: str = "ep-stats"
    app_env: str = "dev"
    app_title: str = "Experimentation Platform Statistics"
    app_description: str = "API for statistical evaluation in Experimentation Platform."

    host: str = "0.0.0.0"
    port: int = 8080

    log_level: str = "info"
    evaluation_pool_size: int = 10
    web_workers: int = 1
