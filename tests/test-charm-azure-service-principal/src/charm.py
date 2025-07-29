#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Application charm that connects to the azure auth integrator provider charm.

This charm is meant to be used only for testing
the azure service principal requires-provides relation.
"""

import logging

from lib.azure_service_principal import (
    AzureServicePrincipalRequirer,
    ServicePrincipalInfoChangedEvent,
    ServicePrincipalInfoGoneEvent,
)
from ops.charm import CharmBase, RelationJoinedEvent
from ops.main import main
from ops.model import ActiveStatus, WaitingStatus

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

        # add relation
        self.framework.observe(
            self.azure_service_principal_client.on.service_principal_info_changed,
            self._on_service_principal_info_changed,
        )

        self.framework.observe(
            self.on[RELATION_NAME].relation_joined, self._on_relation_joined
        )

        self.framework.observe(
            self.azure_service_principal_client.on.service_principal_info_gone,
            self._on_service_principal_info_gone,
        )

        self.framework.observe(self.on.update_status, self._on_update_status)

    def _on_start(self, _) -> None:
        """Only sets an waiting status."""
        self.unit.status = WaitingStatus("Waiting for relation")

    def _on_relation_joined(self, _: RelationJoinedEvent):
        """On Azure credential relation joined."""
        logger.info("Relation_1 joined...")
        self.unit.status = ActiveStatus()

    def _on_service_principal_info_changed(self, e: ServicePrincipalInfoChangedEvent):
        credentials = self.azure_service_principal_client.get_azure_service_principal_info()
        logger.info(f"Credentials changed. New credentials: {credentials}")

    def _on_service_principal_info_gone(self, _: ServicePrincipalInfoGoneEvent):
        logger.info("Credentials gone...")
        self.unit.status = WaitingStatus("Waiting for relation")

    @property
    def _peers(self):
        """Retrieve the peer relation (`ops.model.Relation`)."""
        return self.model.get_relation(PEER)

    def _on_update_status(self, _):
        service_principal_info = self.azure_service_principal_client.get_azure_service_principal_info()
        logger.info(f"Azure service principal client info: {service_principal_info}")

if __name__ == "__main__":
    main(ApplicationCharm)
