import logging
from pathlib import Path

import jubilant
import pytest
import yaml
from helpers import get_application_data

logger = logging.getLogger(__name__)


CHARM_METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
APP_NAME = CHARM_METADATA["name"]
TEST_CHARM_METADATA = yaml.safe_load(
    Path("./tests/integration/test-charm-azure-service-principal/metadata.yaml").read_text()
)
TEST_APP_NAME = TEST_CHARM_METADATA["name"]

RELATION_NAME = "azure-service-principal-credentials"
SECRET_IDENTIFIER = "test-secret"


@pytest.mark.abort_on_fail
def test_build_and_deploy_charm(
    juju: jubilant.Juju, azure_auth_charm_path: Path, test_charm_path: Path
):
    """Tests building and deploying the integrator and the test charm, with proper statuses"""
    juju.deploy(
        azure_auth_charm_path,
        app=APP_NAME,
    )

    juju.deploy(
        test_charm_path,
        app=TEST_APP_NAME,
    )

    juju.wait(jubilant.all_blocked, error=jubilant.any_error)


@pytest.mark.abort_on_fail
def test_config_options(juju: jubilant.Juju):
    """Tests proper handling of configuration parameters."""

    juju.config(APP_NAME, {"subscription-id": "subscription-test", "tenant-id": "tenant-test"})

    # Status should be blocked due to missing "credentials"
    status = juju.wait(
        lambda status: jubilant.all_blocked(status, APP_NAME),
    )
    assert status.apps[APP_NAME].app_status.message == "Missing parameters: ['credentials']"

    secret_uri = juju.add_secret(
        SECRET_IDENTIFIER, {"client-id": "id-test", "client-secret": "secret-test"}
    )
    juju.config(APP_NAME, {"credentials": secret_uri})

    # Status should be blocked because secret has not been granted
    juju.wait(jubilant.all_agents_idle)
    status = juju.wait(
        lambda status: jubilant.all_blocked(status, APP_NAME),
    )
    assert status.apps[APP_NAME].app_status.message == f"Permission for secret '{secret_uri}' has not been granted."

    juju.grant_secret(secret_uri, APP_NAME)
    # All credentials have been provided
    status = juju.wait(
        lambda status: jubilant.all_active(status, APP_NAME),
    )


@pytest.mark.abort_on_fail
def test_relation_creation(juju: jubilant.Juju):
    """Relate charm and wait for the expected changes in status."""
    juju.integrate(APP_NAME, TEST_APP_NAME)
    juju.wait(jubilant.all_active)

    azure_credentials = get_application_data(juju, TEST_APP_NAME, RELATION_NAME)
    logger.debug(azure_credentials)

    assert "subscription-id" in azure_credentials
    assert "tenant-id" in azure_credentials
    assert "secret-extra" in azure_credentials

    assert azure_credentials["subscription-id"] == "subscription-test"
    assert azure_credentials["tenant-id"] == "tenant-test"

    secret_uri = azure_credentials["secret-extra"]
    secret_data = juju.show_secret(secret_uri, reveal=True)
    assert secret_data.content["client-id"] == "id-test"
    assert secret_data.content["client-secret"] == "secret-test"


@pytest.mark.abort_on_fail
def test_secret_updated(juju: jubilant.Juju):
    """Tests updating the secret and having the update propagated to the relation."""
    # Change the value of the secret
    juju.update_secret(
        SECRET_IDENTIFIER, {"client-id": "id-test", "client-secret": "new-secret-value"}
    )
    juju.wait(jubilant.all_active)

    azure_credentials = get_application_data(juju, TEST_APP_NAME, RELATION_NAME)

    assert "subscription-id" in azure_credentials
    assert "tenant-id" in azure_credentials
    assert "secret-extra" in azure_credentials

    secret_uri = azure_credentials["secret-extra"]
    secret_data = juju.show_secret(secret_uri, reveal=True)
    assert secret_data.content["client-id"] == "id-test"
    assert secret_data.content["client-secret"] == "new-secret-value"


@pytest.mark.abort_on_fail
def test_relation_broken(juju: jubilant.Juju):
    """Removes relation and waits for the expected changes in status."""
    juju.remove_relation(APP_NAME, TEST_APP_NAME)

    juju.wait(lambda status: jubilant.all_active(status, APP_NAME), error=jubilant.any_error)

    # Test that charm's status changes to Blocked
    juju.wait(lambda status: jubilant.all_blocked(status, TEST_APP_NAME), error=jubilant.any_error)
