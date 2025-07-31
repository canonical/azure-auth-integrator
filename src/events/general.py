# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Azure Service Principal provider related event handlers."""

import ops
from ops import CharmBase
from ops.charm import ConfigChangedEvent

from constants import AZURE_SERVICE_PRINCIPAL_RELATION_NAME
from core.context import Context
from events.base import BaseEventHandler
from lib.azure_service_principal import AzureServicePrincipalProviderData
from managers.azure_service_principal import AzureServicePrincipalManager
from utils.logging import WithLogging


class GeneralEvents(BaseEventHandler, WithLogging):
    """Class implementing general charm-related event hooks."""

    def __init__(self, charm: CharmBase, context: Context):
        super().__init__(charm, "general")

        self.charm = charm
        self.context = context

        self.azure_service_principal_provider_data = AzureServicePrincipalProviderData(
            self.charm.model, AZURE_SERVICE_PRINCIPAL_RELATION_NAME
        )
        self.azure_service_principal_manager = AzureServicePrincipalManager(
            self.azure_service_principal_provider_data
        )

        self.framework.observe(self.charm.on.update_status, self._on_update_status)
        self.framework.observe(self.charm.on.config_changed, self._on_config_changed)
        self.framework.observe(self.charm.on.secret_changed, self._on_secret_changed)

    def _on_update_status(self, event: ops.UpdateStatusEvent):
        """Handle the update status event."""
        self.azure_service_principal_manager.update(self.context.azure_service_principal)

    def _on_config_changed(self, event: ConfigChangedEvent) -> None:  # noqa: C901
        """Event handler for configuration changed events."""
        # Only execute in the unit leader
        if not self.charm.unit.is_leader():
            return

        self.logger.debug(f"Config changed... Current configuration: {self.charm.config}")
        self.azure_service_principal_manager.update(self.context.azure_service_principal)

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

        self.azure_service_principal_manager.update(self.context.azure_service_principal)
