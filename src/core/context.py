"""Charm context definition and parsing logic."""

from typing import Optional

from ops import ConfigData, Model

from constants import AZURE_SERVICE_PRINCIPAL_MANDATORY_OPTIONS
from core.domain import AzureServicePrincipalInfo
from utils.logging import WithLogging
from utils.secrets import decode_secret_key


class Context(WithLogging):
    """Properties and relations of the charm."""

    def __init__(self, model: Model, config: ConfigData):
        self.model = model
        self.charm_config = config

    @property
    def azure_service_principal(self) -> Optional[AzureServicePrincipalInfo]:
        """Return information related to the Azure service principal parameters."""
        for option in AZURE_SERVICE_PRINCIPAL_MANDATORY_OPTIONS:
            if self.charm_config.get(option) is None:
                return None

        credentials = self.charm_config.get("credentials")
        try:
            secret_dict = decode_secret_key(self.model, credentials)
        except Exception as e:
            self.logger.warning(str(e))
            client_id = ""
            client_secret = ""

        return AzureServicePrincipalInfo(
            subscription_id=self.charm_config.get("subscription-id"),
            tenant_id=self.charm_config.get("tenant-id"),
            client_id=secret_dict["client-id"],
            client_secret=secret_dict["client-secret"],
        )
