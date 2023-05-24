import logging
import os
from typing import Optional

import schema
import yaml


class ConfigEntry:
    def __init__(
        name: str,
        org: str,
        namespace: str,
        permissions: str,
        bucket: Optional[str] = None,
    ):
        self.name = name
        self.org = org
        self.namespace = namespace
        self.bucket = bucket
        self.permissions: str = permissions

    @staticmethod
    def schema() -> dict:
        return {
            "name": str,
            "org": str,
            "namespace": str,
            "permissions": str,
            "bucket": schema.Optional(str),
        }


class Config:
    def __init__():
        self.path: str = os.getenv("CONFIG_PATH", "./config.yml")
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.deployment_name: str = os.getenv("DEPLOYMENT_NAME", "isc")
        self.requested_secrets: list[ConfigEntry] = self._load_config()
        self.influxdb_token: str = os.getenv("INFLUXDB_TOKEN", "")
        self.influxdb_uri: str = os.getenv("INFLUXDB_URI", "localhost")

    def _load_config(self) -> list[ConfigEntry]:
        config_schema = schema.Schema([schema.Use(ConfigEntry.schema())])
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except:
            logging.exception("failed to load config")
        return config_schema.validate(config)
