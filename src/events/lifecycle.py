# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Azure Service Principal provider related event handlers."""

import ops
from charms.azure_auth_integrator.v0.azure_service_principal import (
    AzureServicePrincipalProvider,
    ServicePrincipalInfoRequestedEvent,
)
from ops import CharmBase
from ops.charm import (
    ConfigChangedEvent,
)

from constants import AZURE_SERVICE_PRINCIPAL_RELATION_NAME
from core.context import Context
from events.base import BaseEventHandler
from utils.logging import WithLogging


class LifecycleEvents(BaseEventHandler, WithLogging):
    """Class implementing lifecycle charm-related event hooks."""

    def __init__(self, charm: CharmBase, context: Context):
        super().__init__(charm, "lifecycle")

        self.charm = charm
        self.context = context

        self.azure_service_principal_provider = AzureServicePrincipalProvider(
            self.charm, AZURE_SERVICE_PRINCIPAL_RELATION_NAME
        )

        self.framework.observe(self.charm.on.update_status, self._on_update_status)
        self.framework.observe(self.charm.on.config_changed, self._on_config_changed)
        self.framework.observe(self.charm.on.secret_changed, self._on_secret_changed)

        self.framework.observe(
            self.azure_service_principal_provider.on.service_principal_info_requested,
            self._on_azure_service_principal_info_requested,
        )

    def _on_update_status(self, _event: ops.UpdateStatusEvent):
        """Handle the update status event."""
        self._update_provider_data()

    def _on_config_changed(self, _event: ConfigChangedEvent) -> None:  # noqa: C901
        """Event handler for configuration changed events."""
        # Only execute in the leader unit
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
        self.logger.debug("Updating the provider data.")
        data = self.context.azure_service_principal.to_dict()
        relations = self.model.relations[AZURE_SERVICE_PRINCIPAL_RELATION_NAME]
        for relation in relations:
            self.azure_service_principal_provider.update_response(relation, data)

    def _on_azure_service_principal_info_requested(
        self, _event: ServicePrincipalInfoRequestedEvent
    ):
        """Handle the azure_service_principal `info_requested` event."""
        self.logger.debug("Handling info-requested event.")
        if not self.charm.unit.is_leader():
            return

        self._update_provider_data()
