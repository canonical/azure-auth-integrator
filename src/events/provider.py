# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Azure service principal related event handlers."""

from ops import CharmBase

from constants import AZURE_SERVICE_PRINCIPAL_RELATION_NAME
from core.context import Context
from events.base import BaseEventHandler
from lib.azure_service_principal import (
    AzureServicePrincipalProviderData,
    AzureServicePrincipalProviderEventHandlers,
    ServicePrincipalInfoRequestedEvent,
)
from utils.logging import WithLogging


class AzureServicePrincipalProviderEvents(BaseEventHandler, WithLogging):
    """Class implementing Azure service principal relation event hooks."""

    def __init__(self, charm: CharmBase, context: Context):
        super().__init__(charm, "azure-service-principal-provider")

        self.charm = charm
        self.context = context

        self.azure_provider_data = AzureServicePrincipalProviderData(
            self.charm.model, AZURE_SERVICE_PRINCIPAL_RELATION_NAME
        )
        self.azure_provider = AzureServicePrincipalProviderEventHandlers(
            self.charm, self.azure_provider_data
        )
        self.framework.observe(
            self.azure_provider.on.service_principal_info_requested,
            self._on_azure_service_principal_info_requested,
        )

    def _on_azure_service_principal_info_requested(
        self, event: ServicePrincipalInfoRequestedEvent
    ):
        """Handle the `service-principal-info-requested` event."""
        self.logger.info("On service-principal-info-requested")
        if not self.charm.unit.is_leader():
            return

        self.azure_service_principal_manager.update(self.context.azure_service_principal)
