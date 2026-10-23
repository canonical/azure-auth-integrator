# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the requirer side of the azure_service_principal library."""

import pytest
from charms.azure_auth_integrator.v0.azure_service_principal import (
    AzureServicePrincipalRequirer,
    ServicePrincipalInfoChangedEvent,
)
from ops.charm import CharmBase
from ops.testing import Context, Relation, Secret, State

RELATION_NAME = "azure-service-principal-credentials"

REQUIRER_METADATA = {
    "name": "requirer",
    "requires": {RELATION_NAME: {"interface": "azure_service_principal"}},
}


class RequirerCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.azure_service_principal_client = AzureServicePrincipalRequirer(
            self, relation_name=RELATION_NAME
        )


@pytest.fixture()
def ctx() -> Context:
    return Context(RequirerCharm, meta=REQUIRER_METADATA)


@pytest.mark.parametrize("relation_id", [0, 7])
def test_relation_changed_emits_info_changed(ctx: Context, relation_id: int):
    """The requirer reads the provider data whatever the relation id is."""
    # Arrange
    credentials_secret = Secret(
        tracked_content={"client-id": "clientid", "client-secret": "clientsecret"}
    )
    relation = Relation(
        endpoint=RELATION_NAME,
        id=relation_id,
        remote_app_data={
            "subscription-id": "subscriptionid",
            "tenant-id": "tenantid",
            "secret-extra": credentials_secret.id,
        },
    )
    state_in = State(leader=True, relations=[relation], secrets={credentials_secret})

    # Act
    with ctx(ctx.on.relation_changed(relation), state_in) as manager:
        manager.run()
        info = manager.charm.azure_service_principal_client.get_azure_service_principal_info()

    # Assert
    assert info["subscription-id"] == "subscriptionid"
    assert info["tenant-id"] == "tenantid"
    assert info["client-id"] == "clientid"
    assert info["client-secret"] == "clientsecret"
    assert any(isinstance(e, ServicePrincipalInfoChangedEvent) for e in ctx.emitted_events)
