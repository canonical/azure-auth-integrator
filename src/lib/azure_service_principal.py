import hashlib
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
    get_encoded_dict,
)
from ops.charm import (
    CharmBase,
    CharmEvents,
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationEvent,
)
from ops.framework import EventSource
from ops.model import Relation

from pydantic import (
    Field,
    TypeAdapter
)


logger = logging.getLogger(__name__)


AZURE_SERVICE_PRINCIPAL_REQUIRED_INFO = [
    "subscription-id",
    "tenant-id",
    "client-id",
    "client-secret",
]

def gen_hash(resource_name: str, salt: str) -> str:
    """Generates a consistent hash based on the resource name and salt."""
    hasher = hashlib.sha256()
    hasher.update(f"{resource_name}:{salt}".encode())
    return hasher.hexdigest()[:16]

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
        self.framework.observe(
            self.charm.on[self.relation_name].relation_changed,
            self._on_relation_changed_event,
        )


    def get_azure_service_principal_info(self):
        """Return the Azure service principal info as a dictionary."""
        if not self.relations:
            return {}

        requests = build_model(
            self.interface.repository(self.relations[0].id, self.relations[0].app),
            DataContractV1[AzureServicePrincipalProviderModel],
        ).requests
        if not requests:
            return {}
        request = requests[0]

        return {
            key: getattr(request, key.replace("-", "_"), None)
            for key in AZURE_SERVICE_PRINCIPAL_REQUIRED_INFO
        }

    def _on_relation_broken_event(self, event: RelationBrokenEvent) -> None:
        """Event handler for handling relation_broken event."""
        logger.info("Azure service principal relation broken...")
        getattr(self.on, "service_principal_info_gone").emit(
            event.relation, app=event.app, unit=event.unit
        )

    def _on_relation_changed_event(self, event: RelationChangedEvent) -> None:
        """Notify the charm about the presence of Azure service principal credentials."""
        logger.info(f"Azure service principal relation ({event.relation.name}) changed...")

        repository = self.interface.repository(event.relation.id, event.app)
        data = repository.get_field("data")
        response_model = self.interface.build_model(event.relation.id, component=event.app)
        request_map = TypeAdapter(dict[str, self._request_model]).validate_json(data)

        for response in response_model.requests:
            response_id = response.request_id or gen_hash(response.resource, response.salt)
            request = request_map.get(response_id, None)
            if not request:
                raise ValueError(
                    f"No request matching the response with response_id {response_id}"
                )
            diff = self.compute_diff(event.relation, response, repository, store=False)

            # check if the mandatory options are in the relation data
            contains_required_options = True
            credentials = self.get_azure_service_principal_info()
            missing_options = []
            for configuration_option in AZURE_SERVICE_PRINCIPAL_REQUIRED_INFO:
                if configuration_option not in credentials:
                    contains_required_options = False
                    missing_options.append(configuration_option)

            # emit credential change event only if all mandatory fields are present
            # and there has been a change in credentials
            if contains_required_options and diff:
                getattr(self.on, "service_principal_info_changed").emit(
                    event.relation, app=event.app, unit=event.unit
                )
            else:
                logger.warning(
                    f"Some mandatory fields: {missing_options} are not present, do not emit credential change event!"
                )
        super()._on_relation_changed_event(event)


class AzureServicePrincipalProvider(ResourceProviderEventHandler):
    def __init__(self, charm: CharmBase, relation_name: str):
        ResourceProviderEventHandler.__init__(self, charm, relation_name, RequirerCommonModel)

    def set_initial_response(self, event: ResourceRequestedEvent, data):
        """Set the initial response when a new resource is requested."""
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

    def update_response(self, relation: Relation, data):
        """Update the response to the requirer."""
        requests = self.requests(relation)
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
