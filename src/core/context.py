# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm context definition and parsing logic."""

from ops import ConfigData, Model

from core.domain import AzureServicePrincipalInfo
from utils.logging import WithLogging
from utils.secrets import decode_secret_key


class Context(WithLogging):
    """Properties and relations of the charm."""

    def __init__(self, model: Model, config: ConfigData):
        self.model = model
        self.charm_config = config

    @property
    def azure_service_principal(self) -> AzureServicePrincipalInfo:
        """Return information related to the Azure service principal parameters."""
        credentials = self.charm_config.get("credentials")
        try:
            secret_dict = decode_secret_key(self.model, credentials)
        except Exception as e:
            self.logger.warning(str(e))
            secret_dict = {}

        return AzureServicePrincipalInfo(
            subscription_id=self.charm_config.get("subscription-id"),
            tenant_id=self.charm_config.get("tenant-id"),
            client_id=secret_dict.get("client-id", ""),
            client_secret=secret_dict.get("client-secret", ""),
        )
