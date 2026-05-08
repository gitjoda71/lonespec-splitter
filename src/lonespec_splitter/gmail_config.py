import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class GmailConfig:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        return config

    @property
    def workspace_domain(self) -> str:
        """Get workspace domain from config (e.g., 'workspace.se')."""
        return self.config.get("workspace_domain", "").strip()

    @property
    def service_account_key_path(self) -> str:
        """Get path to service account JSON key."""
        return self.config.get("service_account_key_path", "").strip()

    @property
    def enabled(self) -> bool:
        """Check if Gmail drafting is enabled."""
        return self.config.get("enabled", False)

    def validate(self) -> bool:
        """Validate that required keys are present and files exist."""
        if not self.enabled:
            return True

        if not self.workspace_domain:
            logger.error("Missing 'workspace_domain' in gmail_config.yaml")
            return False

        if not self.service_account_key_path:
            logger.error("Missing 'service_account_key_path' in gmail_config.yaml")
            return False

        key_path = Path(self.service_account_key_path)
        if not key_path.exists():
            logger.error(
                f"Service account key not found: {self.service_account_key_path}"
            )
            return False

        return True
