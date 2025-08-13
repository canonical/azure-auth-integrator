#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Application charm that connects to the azure auth integrator provider charm.

This charm is meant to be used only for testing
the azure service principal requires-provides relation.
"""

import logging

from ops.charm import ActionEvent, CharmBase, RelationJoinedEvent
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

from lib.azure_service_principal import (
    AzureServicePrincipalRequirer,
    ServicePrincipalInfoChangedEvent,
    ServicePrincipalInfoGoneEvent,
)

logger = logging.getLogger(__name__)

RELATION_NAME = "azure-service-principal-credentials"
CONTAINER_NAME = "test-bucket"


class ApplicationCharm(CharmBase):
    """Application charm that relates to Azure auth integrator."""

    def __init__(self, *args):
        super().__init__(*args)

        # Default charm events.
        self.framework.observe(self.on.start, self._on_start)

        self.azure_service_principal_client = AzureServicePrincipalRequirer(self, RELATION_NAME)

        self.framework.observe(
            self.azure_service_principal_client.on.service_principal_info_changed,
            self._on_service_principal_info_changed,
        )
        self.framework.observe(self.on[RELATION_NAME].relation_joined, self._on_relation_joined)
        self.framework.observe(
            self.azure_service_principal_client.on.service_principal_info_gone,
            self._on_service_principal_info_gone,
        )
        self.framework.observe(self.on.update_status, self._on_update_status)
        self.framework.observe(self.on.get_azure_service_principal_info_action, self._on_get_service_principal_info)

    def _on_start(self, _) -> None:
        """Only sets an waiting status."""
        self.unit.status = BlockedStatus("Waiting for relation.")

    def _on_relation_joined(self, _: RelationJoinedEvent):
        """On Azure credential relation joined."""
        logger.info("azure-service-principal-credentials relation joined...")
        self.unit.status = ActiveStatus()

    def _on_service_principal_info_changed(self, e: ServicePrincipalInfoChangedEvent):
        service_principal_info = (
            self.azure_service_principal_client.get_azure_service_principal_info()
        )
        if service_principal_info:
            logger.debug(f"Credentials changed. New credentials: {service_principal_info}")

    def _on_service_principal_info_gone(self, _: ServicePrincipalInfoGoneEvent):
        logger.debug("Credentials gone...")
        self.unit.status = BlockedStatus("Waiting for relation.")

    def _on_update_status(self, _):
        service_principal_info = (
            self.azure_service_principal_client.get_azure_service_principal_info()
        )
        if service_principal_info:
            logger.debug(f"Azure service principal client info: {service_principal_info}")

    def _on_get_service_principal_info(self, event: ActionEvent):
        service_principal_info = (
            self.azure_service_principal_client.get_azure_service_principal_info()
        )
        if service_principal_info:
            event.set_results(service_principal_info)
            logger.debug(f"Azure service principal client info: {service_principal_info}")


if __name__ == "__main__":
    main(ApplicationCharm)
