config = {
    "logging": {
        "version": 1,
        "formatters": {
            "standard": {
                "class": "logging.Formatter",
                "format": "%(asctime)s [%(levelname)-7s] %(name)-35s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "epstats": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    },
}
