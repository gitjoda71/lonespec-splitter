"""Konfiguration för Gmail-drafting (gmail_config.yaml)."""
from __future__ import annotations

import logging
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
            return yaml.safe_load(f) or {}

    @property
    def workspace_domain(self) -> str:
        """Workspace-domän, t.ex. 'workspace.se'."""
        return (self.config.get("workspace_domain") or "").strip()

    @property
    def service_account_key_path(self) -> str:
        """Sökväg till Service Account JSON-nyckel."""
        return (self.config.get("service_account_key_path") or "").strip()

    @property
    def delegated_user(self) -> str:
        """Användare som SA ska impersonera (din egen Gmail-adress).

        Drafts hamnar i denna användares utkasts-mapp.
        """
        return (self.config.get("delegated_user") or "").strip()

    @property
    def enabled(self) -> bool:
        """Är Gmail-drafting aktiverat?"""
        return bool(self.config.get("enabled", False))

    def validate(self) -> bool:
        """Validera att alla obligatoriska fält finns och nycklar existerar."""
        if not self.enabled:
            # OK att vara avstängd — låter splittern ändå köra
            return True

        if not self.workspace_domain:
            logger.error("Saknar 'workspace_domain' i gmail_config.yaml")
            return False

        if not self.delegated_user:
            logger.error(
                "Saknar 'delegated_user' i gmail_config.yaml — "
                "ange din egen Gmail-adress (utkasten hamnar där)"
            )
            return False

        # Sanity-check: delegated_user borde tillhöra workspace_domain
        if "@" in self.delegated_user:
            domain = self.delegated_user.split("@", 1)[1].lower()
            if domain != self.workspace_domain.lower():
                logger.warning(
                    f"delegated_user '{self.delegated_user}' tillhör '{domain}' "
                    f"men workspace_domain är '{self.workspace_domain}' — "
                    f"kontrollera att detta är avsiktligt."
                )

        if not self.service_account_key_path:
            logger.error("Saknar 'service_account_key_path' i gmail_config.yaml")
            return False

        key_path = Path(self.service_account_key_path)
        if not key_path.exists():
            logger.error(
                f"Service account key not found: {self.service_account_key_path}"
            )
            return False

        return True
