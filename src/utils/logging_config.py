"""Configuração centralizada de logging para o CryptoETL."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    """Formata logs como JSON em uma única linha."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str | int | None = None) -> None:
    """Configura logging padrão do projeto.

    Usa texto simples por padrão e JSON quando `LOG_FORMAT=json`.
    """

    resolved_level = level or os.getenv("LOG_LEVEL", "INFO")
    resolved_format = os.getenv("LOG_FORMAT", "text").strip().lower()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(resolved_level)

    if resolved_format == "json":
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(resolved_level)
