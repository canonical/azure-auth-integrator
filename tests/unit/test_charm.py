# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the azure-auth-integrator charm."""

import dataclasses
import json
import logging
from pathlib import Path

from ops.model import ActiveStatus, BlockedStatus
from ops.testing import Context, Relation, Secret, State
import pytest
import yaml

from src.charm import AzureAuthIntegratorCharm

CONFIG = yaml.safe_load(Path("./config.yaml").read_text())
METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())


logger = logging.getLogger(__name__)


@pytest.fixture()
def ctx() -> Context:
    ctx = Context(AzureAuthIntegratorCharm, meta=METADATA, config=CONFIG, unit_id=0)
    return ctx


@pytest.fixture()
def base_state() -> State:
    return State(leader=True)


@pytest.fixture()
def charm_configuration() -> dict:
    return json.loads(json.dumps(CONFIG))


def test_on_start_blocked(ctx: Context[AzureAuthIntegratorCharm], base_state: State):
    """Tests than on start, the status is blocked, waiting for credentials."""
    # Arrange
    state_in = base_state

    # Act
    state_out = ctx.run(ctx.on.start(), state_in)

    # Assert
    assert isinstance(status := state_out.unit_status, BlockedStatus)
    assert "credentials" in status.message


def test_on_start_no_secret_access_blocked(
    ctx: Context[AzureAuthIntegratorCharm], base_state: State, charm_configuration: dict
):
    """Tests that the charm's status is blocked if not granted secret access."""
    # Arrange
    charm_configuration["options"]["subscription-id"]["default"] = "subscriptionid"
    charm_configuration["options"]["tenant-id"]["default"] = "tenantid"
    # This secret does not exist
    charm_configuration["options"]["credentials"]["default"] = "secret:1a2b3c4d5e6f7g8h9i0j"
    ctx = Context(AzureAuthIntegratorCharm, meta=METADATA, config=charm_configuration, unit_id=0)
    state_in = base_state

    # Act
    state_out = ctx.run(ctx.on.start(), state_in)

    # Assert
    assert isinstance(status := state_out.unit_status, BlockedStatus)
    assert "does not exist" in status.message


def test_on_start_active(
    ctx: Context[AzureAuthIntegratorCharm], base_state: State, charm_configuration: dict
):
    """Tests that with all configuration options, the status is active."""
    # Arrange
    credentials_secret = Secret(
        tracked_content={
            "client-id": "clientid",
            "client-secret": "clientsecret",
        }
    )
    charm_configuration["options"]["subscription-id"]["default"] = "subscriptionid"
    charm_configuration["options"]["tenant-id"]["default"] = "tenantid"
    charm_configuration["options"]["credentials"]["default"] = credentials_secret.id
    ctx = Context(AzureAuthIntegratorCharm, meta=METADATA, config=charm_configuration, unit_id=0)
    state_in = dataclasses.replace(base_state, secrets={credentials_secret})

    # Act
    state_out = ctx.run(ctx.on.start(), state_in)

    # Assert
    assert state_out.unit_status == ActiveStatus()


def test_relation_application_data(
    ctx: Context[AzureAuthIntegratorCharm], base_state: State, charm_configuration: dict
):
    """Test that after relating, the charm correctly provides all credentials via the application data."""
    # Arrange
    credentials_secret = Secret(
        tracked_content={
            "client-id": "clientid",
            "client-secret": "clientsecret",
        }
    )
    charm_configuration["options"]["subscription-id"]["default"] = "subscriptionid"
    charm_configuration["options"]["tenant-id"]["default"] = "tenantid"
    charm_configuration["options"]["credentials"]["default"] = credentials_secret.id
    ctx = Context(AzureAuthIntegratorCharm, meta=METADATA, config=charm_configuration, unit_id=0)
    azure_service_principal_relation = Relation(endpoint="azure-service-principal-credentials")
    state_in = dataclasses.replace(
        base_state, relations=[azure_service_principal_relation], secrets={credentials_secret}
    )

    # Act
    state_out = ctx.run(ctx.on.relation_joined(azure_service_principal_relation), state_in)

    # Assert
    assert state_out.unit_status == ActiveStatus()
    provider_data = state_out.get_relation(azure_service_principal_relation.id).local_app_data
    assert provider_data["subscription-id"] == "subscriptionid"
    assert provider_data["tenant-id"] == "tenantid"
    assert provider_data["client-id"] == "clientid"
    assert provider_data["client-secret"] == "clientsecret"
