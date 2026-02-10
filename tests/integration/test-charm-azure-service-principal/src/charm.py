#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Application charm that connects to the azure auth integrator provider charm.

This charm is meant to be used only for testing
the azure service principal requires-provides relation.
"""

import logging

from ops import Relation
from ops.charm import ActionEvent, CharmBase, RelationJoinedEvent
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

from charms.data_platform_libs.v1.data_interfaces import (
    DataContractV1,
    RequirerCommonModel,
    RequirerDataContractV1,
    ResourceCreatedEvent,
    ResourceRequirerEventHandler,
    build_model
)
from lib.azure_service_principal_v1 import (
    AzureServicePrincipalRequirer,
    AzureServicePrincipalProviderModel,
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

        requests = [
            RequirerCommonModel(resource="azure-service-principal"),
        ]
        self.azure_service_principal_client = AzureServicePrincipalRequirer(self, RELATION_NAME)
        
        self.azure_service_principal_client = ResourceRequirerEventHandler(self, RELATION_NAME,
                                                                           requests,
                                                                           response_model=AzureServicePrincipalProviderModel)

        # self.framework.observe(
        #     self.azure_service_principal_client.on.service_principal_info_changed,
        #     self._on_service_principal_info_changed,
        # )
        self.framework.observe(self.on[RELATION_NAME].relation_joined, self._on_relation_joined)
        self.framework.observe(self.azure_service_principal_client.on.resource_created,
                                       self._on_resource_created)
        self.framework.observe(self.azure_service_principal_client.on.resource_entity_created,
                               self._on_resource_entity_created)
        # self.framework.observe(
        #     self.azure_service_principal_client.on.service_principal_info_gone,
        #     self._on_service_principal_info_gone,
        # )
        self.framework.observe(self.on.update_status, self._on_update_status)
        self.framework.observe(
            self.on.get_azure_service_principal_info_action, self._on_get_service_principal_info
        )

    def _on_start(self, _) -> None:
        """Only sets an waiting status."""
        self.unit.status = BlockedStatus("Waiting for relation.")

    def _on_relation_joined(self, _: RelationJoinedEvent):
        """On Azure credential relation joined."""
        logger.info("azure-service-principal-credentials relation joined...")
        self.unit.status = ActiveStatus()

    def _on_resource_created(self, event: ResourceCreatedEvent) -> None:
        logger.info("New relation resource created.")
        response = event.response
        info = {
            "subscription-id" : response.subscription_id,
            "tenant-id" : response.tenant_id,
            "client-id" : response.client_id,
            "client-secret" : response.client_secret
        }
        logger.info(info)
        
    def _on_resource_entity_created(self, event: ResourceCreatedEvent) -> None:
        logger.info("New resource entity created.")
        response = event.response
        info = {
            "subscription-id" : response.subscription_id,
            "tenant-id" : response.tenant_id,
            "client-id" : response.client_id,
            "client-secret" : response.client_secret
        }
        logger.info(info)

        
    # def _on_service_principal_info_changed(self, e: ServicePrincipalInfoChangedEvent):
    #     service_principal_info = (
    #         self.azure_service_principal_client.get_azure_service_principal_info()
    #     )
    #     if service_principal_info:
    #         logger.debug(f"Credentials changed. New credentials: {service_principal_info}")

    # def _on_service_principal_info_gone(self, _: ServicePrincipalInfoGoneEvent):
    #     logger.debug("Credentials gone...")
    #     self.unit.status = BlockedStatus("Waiting for relation.")

    def _on_update_status(self, _):
        pass
        # service_principal_info = (
        #     self.azure_service_principal_client.get_azure_service_principal_info()
        # )
        # if service_principal_info:
        #     logger.debug(f"Azure service principal client info: {service_principal_info}")

    def _on_get_service_principal_info(self, event: ActionEvent):
        if not self.azure_service_principal_relation:
            return
        requests = build_model(self.azure_service_principal_client.interface.repository(self.azure_service_principal_relation.id,
                                                                self.azure_service_principal_relation.app),
                        DataContractV1[AzureServicePrincipalProviderModel]).requests
        logger.info(requests)

    @property
    def azure_service_principal_relation(self) -> Relation | None:
        """Return the azure_service_principal relation if present."""
        if not hasattr(self, "azure_service_principal_client"):
            logger.debug("No azure_service_principal relation client")
            return None
        return self.azure_service_principal_client.relations[0] if len(self.azure_service_principal_client.relations) else None

if __name__ == "__main__":
    main(ApplicationCharm)
