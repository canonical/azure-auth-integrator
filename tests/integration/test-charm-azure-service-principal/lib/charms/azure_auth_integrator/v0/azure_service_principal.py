# Copyright 2026 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Library to manage Azure Service Principal credentials.

The design of the interface and the library has been specified in:
https://docs.google.com/document/d/1RvpKpL2nxwzFmPHX9NJGe1h3J0lPQ_YltXROIB1TicI/edit?tab=t.0.

This library contains a Requirer and a Provider for handling the relation and transmission
of Azure Service Principal credentials.

It makes use of the `data_interfaces` Charmhub hosted-library in order to transmit sensitive
information as secrets. The source code is located in https://github.com/canonical/data-platform-libs

The library also provides custom events to relay information about the status of the
credentials.


#### Requirer charm

On the requirer side of the charm, instantiate an `AzureServicePrincipalRequirer` object:

```python
# charm.py

from charms.azure_auth_integrator.v0.azure_service_principal import (
    AzureServicePrincipalRequirer,
)

class RequirerCharm(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)

            ...

        self.azure_service_principal_client = AzureServicePrincipalRequirer(
                    self,
                    relation_name="azure-service-principal-credentials"
                )
```


Using this instance of class `AzureServicePrincipalRequirer`, the requirer charm then needs to listen
to custom events `service_principal_info_changed` and `service_principal_info_gone` and handle them
 appropriately in the charm code.

- The event `service_principal_info_changed` is fired whenever `azure-auth-integrator` has written
new data to the relation databag, which needs to be handled by the requirer charm by updating its
state with the new Azure Service Principal connection information.
- The event `service_principal_info_gone` is fired when the relation with `azure-auth-integrator` is
broken, which needs to be handled by the requirer charm by updating its state to not use the Azure
Service principal connection information anymore.

```python
# charm.py

from charms.azure_auth_integrator.v0.azure_service_principal import (
    AzureServicePrincipalRequirer,
    ServicePrincipalInfoChangedEvent,
    ServicePrincipalInfoGoneEvent,
)

class RequirerCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)

            self.azure_service_principal_client = AzureServicePrincipalRequirer(
                    self,
                        relation_name="azure-service-prinicpal-credentials"
                )

        # Observe custom events
        self.framework.observe(
            self.azure_service_principal_client.on.service_principal_info_changed,
            self._on_service_principal_info_changed,
        )
        self.framework.observe(
            self.azure_service_principal_client.on.service_principal_info_gone,
            self._on_service_principal_info_gone,
        )


    def _on_service_principal_info_changed(self, event: ServicePrincipalInfoChangedEvent):
        # access and consume data from the provider
        connection_info = self.azure_service_principal_client.get_azure_service_principal_info()
        process_connection_info(connection_info)

    def _on_service_principal_info_gone(self, event: ServicePrincipalInfoGoneEvent):
        # notify charm code that credentials are removed
        process_connection_info(None)

```

The latest Azure Service Principal connection information shared by the `azure-auth-integrator` over
the relation can be fetched using the utility method `get_azure_service_principal_info()` available
in the `AzureServicePrincipalRequirer` instance, which returns a dictionary:

```python
        AzureServicePrincipalInfo = {
            "subscription-id": str,
            "tenant-id": str,
            "client-id": str,
            "client-secret": str,
        }
```


#### Provider charm

If you need a provider charm that only relays the Azure Service Principal credentials to a
requirer, then you probably don't need to implement your own provider, and can just use
`azure-auth-integrator`: https://github.com/canonical/azure-auth-integrator

On the provider side of the charm, instantiate an `AzureServicePrincipalProvider` object:

```python
# charm.py

from charms.azure_auth_integrator.v0.azure_service_principal import (
    AzureServicePrincipalProvider,
)

class ProviderCharm(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)

            ...

        self.azure_service_principal_provider = AzureServicePrincipalProvider(
            self,
            relation_name="azure-service-principal-credentials"
        )

```

Using this instance of class `AzureServicePrincipalProvider`, the provider charm then needs to listen
to the custom event `service_principal_info_requested`, which is emitted when the integration with
requirer charm is initially made.

The relation data can be set and/or updated with the `update_response` method. To make sure the data
stays updated, make sure to call this method whenever any of the provided credentials may have changed:

```python
# charm.py

from charms.azure_auth_integrator.v0.azure_service_principal import (
    AzureServicePrincipalProvider,
    ServicePrincipalInfoRequestedEvent,
)

AZURE_SERVICE_PRINCIPAL_RELATION_NAME = "azure-service-principal-credentials"

class ProviderCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)

        self.azure_service_principal_provider = AzureServicePrincipalProvider(
            self,
            relation_name=AZURE_SERVICE_PRINCIPAL_RELATION_NAME
        )

        # Observe custom events
        self.framework.observe(
            self.azure_service_principal_provider.on.service_principal_info_requested,
            self._update_provider_data,
        )
        # Also observe events in which data may have changed
        self.framework.observe(
            self.charm.on_config_changed,
            self._update_provider_data,
        )


    def _update_provider_data(self, event: ServicePrincipalInfoRequestedEvent):
        # Gather data as a dictionary
        data = ...
        # Get instances of the relation
        relations = self.model.relations[AZURE_SERVICE_PRINCIPAL_RELATION_NAME]
        for relation in relations:
            self.azure_service_principal_provider.update_response(relation, data)

```


"""

# The unique Charmhub library identifier, never change it
LIBID = "d414f5220cf348f8bad08f13e6ec4a5b"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 3


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

