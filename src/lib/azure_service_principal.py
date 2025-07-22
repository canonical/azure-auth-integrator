"""Logic for the provider and requirer side of the azure_service_principal interface."""

import logging
from typing import Dict, List, Optional

from charms.data_platform_libs.v0.data_interfaces import (
    EventHandlers,
    ProviderData,
    RequirerData,
    RequirerEventHandlers,
)
from ops import Model
from ops.charm import (
    CharmBase,
    CharmEvents,
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationEvent,
    RelationJoinedEvent,
    SecretChangedEvent,
)
from ops.framework import EventSource
from ops.model import Relation


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


class ContainerEvent(ServicePrincipalEvent):
    """Base class for events that include the container."""

    @property
    def container(self) -> Optional[str]:
        """Returns the container name."""
        if not self.relation.app:
            return None

        return self.relation.data[self.relation.app].get("container", "")


class ServicePrincipalInfoRequestedEvent(ContainerEvent):
    """Event for requesting data from the interface."""

    pass


class ServicePrincipalInfoChangedEvent(ContainerEvent):
    """Event for changing data from the interface."""

    pass


class ServicePrincipalInfoGoneEvent(ContainerEvent):
    """Event for the removal of data from the interface."""

    pass


class AzureServicePrincipalProviderEvents(CharmEvents):
    """Events for the AzureServicePrincipalProvider side implementation."""

    service_principal_info_requested = EventSource(ServicePrincipalInfoRequestedEvent)


class AzureServicePrincipalRequirerEvents(CharmEvents):
    """Events for the AzureServicePrincipalRequirer side implementation."""

    service_principal_info_changed = EventSource(ServicePrincipalInfoChangedEvent)
    service_principal_info_gone = EventSource(ServicePrincipalInfoGoneEvent)


class AzureServicePrincipalRequirerData(RequirerData):
    """Data abstraction of the requirer side of Azure service principal relation."""

    SECRET_FIELDS = ["client-secret"]

    def __init__(self, model, relation_name: str, container: Optional[str] = None):
        super().__init__(
            model,
            relation_name,
        )
        self.container = container


class AzureServicePrincipalRequirerEventHandlers(RequirerEventHandlers):
    """Event handlers for for requirer side of Azure service principal relation."""

    on = AzureServicePrincipalRequirerEvents()  # pyright: ignore[reportAssignmentType]

    def __init__(self, charm: CharmBase, relation_data: AzureServicePrincipalRequirerData):
        super().__init__(charm, relation_data)

        self.relation_name = relation_data.relation_name
        self.charm = charm
        self.local_app = self.charm.model.app
        self.local_unit = self.charm.unit

        self.framework.observe(
            self.charm.on[self.relation_name].relation_joined, self._on_relation_joined_event
        )
        self.framework.observe(
            self.charm.on[self.relation_name].relation_changed, self._on_relation_changed_event
        )

        self.framework.observe(
            self.charm.on[self.relation_name].relation_broken,
            self._on_relation_broken_event,
        )

    def _on_relation_joined_event(self, event: RelationJoinedEvent) -> None:
        """Event emitted when the Azure service principal relation is joined."""
        logger.info(f"Azure service principal relation ({event.relation.name}) joined...")
        if self.container is None:
            self.container = f"relation-{event.relation.id}"
        event_data = {"container": self.container}
        self.relation_data.update_relation_data(event.relation.id, event_data)

    def get_azure_service_principal_info(self) -> Dict[str, str]:
        """Return the Azure service principal info as a dictionary."""
        for relation in self.relations:
            if relation and relation.app:
                info = self.relation_data.fetch_relation_data([relation.id])[relation.id]
                if not all(param in info for param in AZURE_SERVICE_PRINCIPAL_REQUIRED_INFO):
                    continue
                return info
        return {}

    def _on_relation_changed_event(self, event: RelationChangedEvent) -> None:
        """Notify the charm about the presence of Azure service principal credentials."""
        logger.info(f"Azure service principal relation ({event.relation.name}) changed...")

        diff = self._diff(event)
        if any(newval for newval in diff.added if self.relation_data._is_secret_field(newval)):
            self.relation_data._register_secrets_to_relation(event.relation, diff.added)

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

    def _on_secret_changed_event(self, event: SecretChangedEvent):
        """Event handler for handling a new value of a secret."""
        if not event.secret.label:
            return

        relation = self.relation_data._relation_from_secret_label(event.secret.label)
        if not relation:
            logging.info(
                f"Received secret {event.secret.label} but couldn't parse, seems irrelevant."
            )
            return

        if event.secret.label != self.relation_data._generate_secret_label(
            relation.name,
            relation.id,
            "extra",
        ):
            logging.info("Secret is not relevant for us.")
            return

        if relation.app == self.charm.app:
            logging.info("Secret changed event ignored for Secret Owner")

        remote_unit = None
        for unit in relation.units:
            if unit.app != self.charm.app:
                remote_unit = unit

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
                relation, app=relation.app, unit=remote_unit
            )
        else:
            logger.warning(
                f"Some mandatory fields: {missing_options} are not present, do not emit credential change event!"
            )

    def _on_relation_broken_event(self, event: RelationBrokenEvent) -> None:
        """Event handler for handling relation_broken event."""
        logger.info("Azure service principal relation broken...")
        getattr(self.on, "service_principal_info_gone").emit(
            event.relation, app=event.app, unit=event.unit
        )

    @property
    def relations(self) -> List[Relation]:
        """The list of Relation instances associated with this relation_name."""
        return list(self.charm.model.relations[self.relation_name])


class AzureServicePrincipalRequires(
    AzureServicePrincipalRequirerData, AzureServicePrincipalRequirerEventHandlers
):
    """The requirer side of Azure service principal relation."""

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str,
        container: Optional[str] = None,
    ):
        AzureServicePrincipalRequirerData.__init__(self, charm.model, relation_name, container)
        AzureServicePrincipalRequirerEventHandlers.__init__(self, charm, self)


class AzureServicePrincipalProviderData(ProviderData):
    """The Data abstraction of the provider side of Azure service principal relation."""

    def __init__(self, model: Model, relation_name: str) -> None:
        super().__init__(model, relation_name)


class AzureServicePrincipalProviderEventHandlers(EventHandlers):
    """The event handlers related to provider side of Azure service principal relation."""

    on = AzureServicePrincipalProviderEvents()

    def __init__(
        self,
        charm: CharmBase,
        relation_data: AzureServicePrincipalProviderData,
        unique_key: str = "",
    ):
        super().__init__(charm, relation_data, unique_key)
        self.relation_data = relation_data

    def _on_relation_changed_event(self, event: RelationChangedEvent):
        if not self.charm.unit.is_leader():
            return
        diff = self._diff(event)
        if "container" in diff.added:
            self.on.service_principal_info_requested.emit(
                event.relation, app=event.app, unit=event.unit
            )


class AzureServicePrincipalProvides(
    AzureServicePrincipalProviderData, AzureServicePrincipalProviderEventHandlers
):
    """The provider side of the Azure service principal relation."""

    def __init__(self, charm: CharmBase, relation_name: str) -> None:
        AzureServicePrincipalProviderData.__init__(self, charm.model, relation_name)
        AzureServicePrincipalProviderEventHandlers.__init__(self, charm, self)
