import logging
from typing import Dict

from charms.data_platform_libs.v1.data_interfaces import (
    DataContractV1,
    ExtraSecretStr,
    RequirerCommonModel,
    ResourceProviderModel,
    ResourceRequirerEventHandler,
    build_model
)
from ops.charm import (
    CharmBase,
    CharmEvents,
    RelationEvent
)
from ops.framework import EventSource

from pydantic import Field


logger = logging.getLogger(__name__)

class ServicePrincipalEvent(RelationEvent):
    """Base class for Azure service principal events."""
    pass


class ServicePrincipalInfoChangedEvent(ServicePrincipalEvent):
    """Event for changing data from the interface."""
    pass


class ServicePrincipalInfoGoneEvent(ServicePrincipalEvent):
    """Event for the removal of data from the interface."""
    pass

class AzureServicePrincipalRequirerEvents(CharmEvents):
    """Events for the AzureServicePrincipalRequirer side implementation."""
    service_principal_info_changed = EventSource(ServicePrincipalInfoChangedEvent)
    service_principal_info_gone = EventSource(ServicePrincipalInfoGoneEvent)


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
    on = AzureServicePrincipalRequirerEvents()  # pyright: ignore[reportAssignmentType]
    
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

    def get_azure_service_principal_info(self):
        """Return the Azure service principal info as a dictionary."""
        if not self.relations:
            return
        
        requests = build_model(self.interface.repository(
            self.relations[0].id, self.relations[0].app),
                               DataContractV1[AzureServicePrincipalProviderModel]).requests[0]
        
        logger.info(requests)
        logger.info(type(requests))
        return {
            "subscription-id": requests.subscription_id,
            "tenant-id": requests.tenant_id,
            "client-id": requests.client_id,
            "client-secret": requests.client_secret
        }
        
