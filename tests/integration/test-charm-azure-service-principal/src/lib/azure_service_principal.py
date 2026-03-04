import logging
from typing import Dict

from charms.data_platform_libs.v1.data_interfaces import (
    BaseCommonModel,
    EventHandlers,
    ExtraSecretStr,
    OpsRelationRepositoryInterface,
    SecretString,
)
from ops.charm import (
    CharmBase,
    CharmEvents,
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationJoinedEvent,
    RelationEvent,
    SecretChangedEvent,
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


class ServicePrincipalEvent(RelationEvent):
    """Base class for Azure service principal events."""

    pass


class ServicePrincipalInfoRequestedEvent(ServicePrincipalEvent):
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


class AzureServicePrincipalProviderEvents(CharmEvents):
    """Events for the AzureServicePrincipalProvider side implementation."""

    service_principal_info_requested = EventSource(ServicePrincipalInfoRequestedEvent)


class AzureServicePrincipalProviderModel(BaseCommonModel):
    """Data abstraction of the provider side of Azure service principal relation."""

    subscription_id: str = Field(default="")
    tenant_id: str = Field(default="")
    client_id: ExtraSecretStr
    client_secret: ExtraSecretStr

    secret_extra: SecretString | None = Field(default=None)


class AzureServicePrincipalRequirer(EventHandlers):
    """The requirer side of Azure service principal relation."""

    on = AzureServicePrincipalRequirerEvents()  # pyright: ignore[reportAssignmentType]

    def __init__(self, charm: CharmBase, relation_name: str, unique_key: str = ""):
        super().__init__(charm, relation_name, unique_key)

        self.relation_name = relation_name
        self.response_model = AzureServicePrincipalProviderModel
        self.interface = OpsRelationRepositoryInterface(
            charm.model, relation_name, self.response_model
        )

        self.framework.observe(
            self.charm.on[self.relation_name].relation_changed, self._on_relation_changed_event
        )

        self.framework.observe(
            self.charm.on[self.relation_name].relation_broken,
            self._on_relation_broken_event,
        )

        self.framework.observe(self.charm.on.secret_changed, self._on_secret_changed_event)

    def get_azure_service_principal_info(self) -> Dict[str, str]:
        """Return the Azure service principal info as a dictionary."""
        if not self.relations:
            return {}

        model = self.interface.build_model(self.relations[0].id, component=self.relations[0].app)
        if not model:
            return {}

        return {
            key.replace("_", "-"): getattr(model, key)
            for key in vars(model)
            if (value := getattr(model, key)) is not None
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

        # Copy response to the local application databag
        model = self.interface.build_model(
            event.relation.id, component=self.relations[event.relation.id].app
        )
        self.interface.write_model(event.relation.id, model)

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

    def _on_secret_changed_event(self, _event: SecretChangedEvent) -> None:
        """Event handler for handling a new value of a secret."""
        pass


class AzureServicePrincipalProvider(EventHandlers):
    """The provider side of Azure service principal relation."""

    on = AzureServicePrincipalProviderEvents()  # pyright: ignore[reportAssignmentType]

    def __init__(self, charm: CharmBase, relation_name: str, unique_key: str = ""):
        super().__init__(charm, relation_name, unique_key)

        self.response_model = AzureServicePrincipalProviderModel
        self.interface = OpsRelationRepositoryInterface(
            charm.model, relation_name, self.response_model
        )

        self.framework.observe(
            self.charm.on[self.relation_name].relation_joined,
            self._on_relation_joined_event,
        )

        self.framework.observe(
            self.charm.on[self.relation_name].relation_changed, self._on_relation_changed_event
        )

        self.framework.observe(self.charm.on.secret_changed, self._on_secret_changed_event)

    def _on_relation_joined_event(self, event: RelationJoinedEvent) -> None:
        """Event handler for handling the relation_joined event."""
        logger.info("Azure service principal relation joined...")

        if not self.charm.unit.is_leader():
            return

        self.on.service_principal_info_requested.emit(
            event.relation, app=event.app, unit=event.unit
        )

    def _on_relation_changed_event(self, _event: RelationChangedEvent) -> None:
        """Event handler for handling the relation_changed event."""
        pass

    def _on_secret_changed_event(self, _event: SecretChangedEvent) -> None:
        """Event handler for handling a new value of a secret."""
        pass

    def update_response(self, relation: Relation, response_data) -> None:
        """Update the response to the requirer."""
        model = self.interface.build_model(relation.id)
        model.subscription_id = response_data["subscription-id"]
        model.tenant_id = response_data["tenant-id"]
        for field in ("client-id", "client-secret"):
            attr_name = field.replace("-", "_")
            setattr(model, attr_name, response_data[field])
        self.interface.write_model(relation.id, model)
