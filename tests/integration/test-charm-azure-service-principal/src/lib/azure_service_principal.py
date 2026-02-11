import logging

from charms.data_platform_libs.v1.data_interfaces import (
    DataContractV1,
    ExtraSecretStr,
    RequirerCommonModel,
    ResourceProviderEventHandler,
    ResourceProviderModel,
    ResourceRequestedEvent,
    ResourceRequirerEventHandler,
    build_model,
)
from ops.charm import (
    CharmBase,
    CharmEvents,
    RelationBrokenEvent,
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
        self.framework.observe(
            self.on.resource_requested,
            self._on_resource_requested,
        )

    def update_provider_data(self, data):
        """Update the contents of the relation data bag."""
        for relation in self.relations:
            model = build_model(self.interface.repository(
                    relation.id, relation.app
                    ),
                    DataContractV1[AzureServicePrincipalProviderModel],
                )
            for request in model.requests:
                request.subscription_id = data["subscription-id"]
                request.tenant_id = data["tenant-id"]
                for key in ("client-id", "client-secret"):
                    setattr(request, key, data[key])
            self.interface.write_model(relation.id, model) 

    def _on_resource_requested(self, event: ResourceRequestedEvent):
        pass
