import logging
from typing import Dict

from charms.data_platform_libs.v1.data_interfaces import (
    ExtraSecretStr,
    RequirerCommonModel,
    ResourceProviderModel,
    ResourceRequirerEventHandler,
)
from ops.charm import (
    CharmBase
)

from pydantic import Field


logger = logging.getLogger(__name__)


class AzureServicePrincipalRequirerModel(RequirerCommonModel):
    """Data abstraction of the requirer side of Azure service principal relation."""
    client_id: ExtraSecretStr
    client_secret: ExtraSecretStr


class AzureServicePrincipalProviderModel(ResourceProviderModel):
    """Data abstraction of the provider side of Azure service principal relation."""
    subscription_id: str = Field(default="")
    tenant_id: str = Field(default="")
    client_id: ExtraSecretStr
    client_secret: ExtraSecretStr


class AzureServicePrincipalRequirer(ResourceRequirerEventHandler):
    def __init__(
            self,
            charm: CharmBase,
            relation_name: str,
    ):
        requests = [
            RequirerCommonModel(resource="azure-service-principal"),
        ]
        ResourceRequirerEventHandler.__init__(self, charm, relation_name, requests,
                                              response_model=AzureServicePrincipalProviderModel)

    def get_azure_service_principal_info(self) -> Dict[str, str]:
        """Return the Azure service principal info as a dictionary."""
