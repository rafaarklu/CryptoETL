"""Carregadores de dados para o pipeline ETL."""

from src.loaders.postgres_loader import PostgresLoader

__all__ = ["PostgresLoader"]
