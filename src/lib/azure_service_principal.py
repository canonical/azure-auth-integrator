import logging

from charms.data_platform_libs.v1.data_interfaces import (
    AuthenticationUpdatedEvent,
    DataContractV1,
    ExtraSecretStr,
    RequirerCommonModel,
    ResourceProviderEventHandler,
    ResourceProviderModel,
    ResourceRequirerEventHandler,
    ResourceRequestedEvent,
    build_model,
)
from ops.charm import (
    CharmBase,
    CharmEvents,
    RelationBrokenEvent,
    RelationEvent,
)
from ops.framework import EventSource
from ops.model import Relation

from pydantic import Field


logger = logging.getLogger(__name__)


class ServicePrincipalEvent(RelationEvent):
    """Base class for Azure service principal events."""

    pass

class ServicePrincipalInfoRequestedEvent(ResourceRequestedEvent):
    """Event for requesting data from the interface."""
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
    authentication_updated = EventSource(AuthenticationUpdatedEvent)


class AzureServicePrincipalRequirerModel(RequirerCommonModel):
    """Data abstraction of the requirer side of Azure service principal relation."""
    subscription_id: str = Field(default="")
    tenant_id: str = Field(default="")
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
            AzureServicePrincipalRequirerModel(resource="azure-service-principal"),
        ]

        ResourceRequirerEventHandler.__init__(
            self, charm, relation_name, requests, response_model=AzureServicePrincipalProviderModel
        )

        self.framework.observe(
            self.charm.on[self.relation_name].relation_broken,
            self._on_relation_broken_event,
        )

    def get_azure_service_principal_info(self):
        """Return the Azure service principal info as a dictionary."""
        if not self.relations:
            return

        requests = build_model(
            self.interface.repository(self.relations[0].id, self.relations[0].app),
            DataContractV1[AzureServicePrincipalProviderModel],
        ).requests[0]

        return {
            "subscription-id": requests.subscription_id,
            "tenant-id": requests.tenant_id,
            "client-id": requests.client_id,
            "client-secret": requests.client_secret,
        }

    def _on_relation_broken_event(self, event: RelationBrokenEvent) -> None:
        """Event handler for handling relation_broken event."""
        logger.info("Azure service principal relation broken...")
        getattr(self.on, "service_principal_info_gone").emit(
            event.relation, app=event.app, unit=event.unit
        )

class AzureServicePrincipalProvider(ResourceProviderEventHandler):

    def __init__(
            self,
            charm: CharmBase,
            relation_name: str
    ):
        ResourceProviderEventHandler.__init__(
            self, charm, relation_name, RequirerCommonModel
        )
        # self.framework.observe(
        #     self.charm.on[self.relation_name].relation_joined,
        #     self._on_relation_joined_event,
        # )

    def set_response(self, event: ResourceRequestedEvent, data):
        """Set the initial response when a new resource is requested."""
        data = self.context.azure_service_principal.to_dict()
        response = AzureServicePrincipalProviderModel(
            salt=event.request.salt,
            request_id=event.request.request_id,
            resource="azure-service-principal",
            subscription_id=data["subscription-id"],
            tenant_id=data["tenant-id"],
            client_id=data["client-id"],
            client_secret=data["client-secret"],
        )
        self.set_response(event.relation.id, response)

        
    def update_reponse(self, relation: Relation, data):
        """Update the response to the requirer."""
        requests = self.azure_service_principal_provider.requests(relation)
        for request in requests:
            new_response = AzureServicePrincipalProviderModel(
                salt=request.salt,
                request_id=request.request_id,
                resource="azure-service-principal",
                subscription_id=data["subscription-id"],
                tenant_id=data["tenant-id"],
                client_id=data["client-id"],
                client_secret=data["client-secret"],
            )
            self.set_response(relation.id, new_response)
        
