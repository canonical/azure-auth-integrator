import logging

from charms.data_platform_libs.v1.data_interfaces import (
    DataContractV1,
    ExtraSecretStr,
    RequirerCommonModel,
    ResourceProviderEventHandler,
    ResourceProviderModel,
    ResourceRequestedEvent,
    ResourceRequirerEventHandler,
    ResourceRequiresEvents,
    build_model,
)
from ops.charm import (
    CharmBase,
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationJoinedEvent,
    RelationEvent,
)
from ops.framework import EventSource
from ops.model import Relation

from pydantic import (
    Field,
)


logger = logging.getLogger(__name__)


AZURE_SERVICE_PRINCIPAL_REQUIRED_INFO = [
    "subscription-id",
    "tenant-id",
    "client-id",
    "client-secret",
]

# Fields that are populated in the relation databag by default in data_interfaces.py
# but are not relevant for the requirer
DATABAG_IRRELEVANT_FIELDS = ["request-id", "resource", "salt", "secret-extra"]


class ServicePrincipalEvent(RelationEvent):
    """Base class for Azure service principal events."""

    pass


class ServicePrincipalInfoChangedEvent(ServicePrincipalEvent):
    """Event for changing data from the interface."""

    pass


class ServicePrincipalInfoGoneEvent(ServicePrincipalEvent):
    """Event for the removal of data from the interface."""

    pass


class AzureServicePrincipalRequirerEvents(ResourceRequiresEvents):
    """Events for the AzureServicePrincipalRequirer side implementation."""

    service_principal_info_changed = EventSource(ServicePrincipalInfoChangedEvent)
    service_principal_info_gone = EventSource(ServicePrincipalInfoGoneEvent)


class AzureServicePrincipalProviderModel(ResourceProviderModel):
    """Data abstraction of the provider side of Azure service principal relation."""

    subscription_id: str = Field(default="")
    tenant_id: str = Field(default="")
    client_id: ExtraSecretStr
    client_secret: ExtraSecretStr


class AzureServicePrincipalRequirer(ResourceRequirerEventHandler):
    """The requirer side of Azure service principal relation."""

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
        self.component = self.charm.app

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
            key.replace("_", "-"): getattr(request, key)
            for key in vars(request)
            if (value := getattr(request, key)) is not None
            and key.replace("_", "-") not in DATABAG_IRRELEVANT_FIELDS
        }

    def _on_relation_broken_event(self, event: RelationBrokenEvent) -> None:
        """Event handler for handling relation_broken event."""
        logger.info("Azure service principal relation broken...")
        getattr(self.on, "service_principal_info_gone").emit(
            event.relation, app=event.app, unit=event.unit
        )

    def _on_relation_changed_event(self, event: RelationChangedEvent) -> None:
        """Notify the charm about the presence of Azure service principal credentials."""
        super()._on_relation_changed_event(event)
        logger.info(f"Azure service principal relation ({event.relation.name}) changed...")

        # check if the mandatory options are in the relation data
        contains_required_options = True
        credentials = self.get_azure_service_principal_info()
        missing_options = []
        for configuration_option in AZURE_SERVICE_PRINCIPAL_REQUIRED_INFO:
            if configuration_option not in credentials:
                contains_required_options = False
                missing_options.append(configuration_option)

        # emit credential change event only if all mandatory fields are present
        if contains_required_options:
            getattr(self.on, "service_principal_info_changed").emit(
                event.relation, app=event.app, unit=event.unit
            )
        else:
            logger.warning(
                f"Some mandatory fields: {missing_options} are not present, do not emit credential change event!"
            )


class AzureServicePrincipalProvider(ResourceProviderEventHandler):
    """The provider side of Azure service principal relation."""

    def __init__(self, charm: CharmBase, relation_name: str):
        ResourceProviderEventHandler.__init__(self, charm, relation_name, RequirerCommonModel)

        self.framework.observe(
            self.charm.on[self.relation_name].relation_joined,
            self._on_relation_joined_event,
        )

    def _on_relation_joined_event(self, event: RelationJoinedEvent) -> None:
        """Event handler for handling the relation_created event."""
        logger.info("Azure service principal relation created...")

        requests = self.requests(event.relation)
        logger.warning(requests)
        if requests and requests[0].version == "v0":
            # For compatibility with older versions of the library
            # that don't use data_interfaces.py `v1`
            logger.info("resource-requested event has not been emitted. Emitting manually...")
            getattr(self.on, "resource_requested").emit(
                event.relation, app=event.app, unit=event.unit, request=requests[0]
            )

    def update_response(self, relation: Relation, data):
        """Update the response to the requirer."""
        requests = self.requests(relation)
        for request in requests:
            logger.debug(request)
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
