# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Azure Service Principal provider related event handlers."""

import ops
from ops import CharmBase
from ops.charm import ConfigChangedEvent

from constants import AZURE_SERVICE_PRINCIPAL_RELATION_NAME
from core.context import Context
from events.base import BaseEventHandler
from lib.azure_service_principal import (
    AzureServicePrincipalProviderData,
    AzureServicePrincipalProviderEventHandlers,
    ServicePrincipalInfoRequestedEvent,
    )
from utils.logging import WithLogging


class LifecycleEvents(BaseEventHandler, WithLogging):
    """Class implementing lifecycle charm-related event hooks."""

    def __init__(self, charm: CharmBase, context: Context):
        super().__init__(charm, "lifecycle")

        self.charm = charm
        self.context = context

        self.azure_service_principal_provider_data = AzureServicePrincipalProviderData(
            self.charm.model, AZURE_SERVICE_PRINCIPAL_RELATION_NAME
        )
        self.azure_service_principal_provider = AzureServicePrincipalProviderEventHandlers(
            self.charm, self.azure_service_principal_provider_data
        )

        self.framework.observe(self.charm.on.update_status, self._on_update_status)
        self.framework.observe(self.charm.on.config_changed, self._on_config_changed)
        self.framework.observe(self.charm.on.secret_changed, self._on_secret_changed)
        self.framework.observe(
            self.azure_service_principal_provider.on.service_principal_info_requested,
            self._on_azure_service_principal_info_requested,
        )

    def _on_update_status(self, event: ops.UpdateStatusEvent):
        """Handle the update status event."""
        self._update_provider_data()

    def _on_config_changed(self, event: ConfigChangedEvent) -> None:  # noqa: C901
        """Event handler for configuration changed events."""
        # Only execute in the unit leader
        if not self.charm.unit.is_leader():
            return

        self.logger.debug(f"Config changed... Current configuration: {self.charm.config}")
        self._update_provider_data()

    def _on_secret_changed(self, event: ops.SecretChangedEvent):
        """Handle the secret changed event.

        When a secret is changed, it is first checked that whether this particular secret
        is used in the charm's config. If yes, the secret is to be updated in the relation
        databag.
        """
        # Only execute in the unit leader
        if not self.charm.unit.is_leader():
            return

        if not self.charm.config.get("credentials"):
            return

        secret = event.secret
        if self.charm.config.get("credentials") != secret.id:
            return

        self._update_provider_data()

    def _update_provider_data(self):
        """Update the contents of the relation data bag."""
        if (
            len(self.azure_service_principal_provider_data.relations) > 0
            and self.context.azure_service_principal
        ):
            for relation in self.azure_service_principal_provider_data.relations:
                self.azure_service_principal_provider_data.update_relation_data(
                    relation.id, self.context.azure_service_principal.to_dict()
                )

    def _on_azure_service_principal_info_requested(
        self, event: ServicePrincipalInfoRequestedEvent
    ):
        """Handle the `service-principal-info-requested` event."""
        self.logger.info("On service-principal-info-requested")
        if not self.charm.unit.is_leader():
            return

        self.azure_service_principal_manager.update(self.context.azure_service_principal)
