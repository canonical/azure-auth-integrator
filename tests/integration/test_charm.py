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
TEST_APP_UNIT_NAME = f"{TEST_APP_NAME}/0"

RELATION_NAME = "azure-service-principal-credentials"
SECRET_IDENTIFIER = "test-secret"

SUBSCRIPTION_ID_TEST_VALUE = "subscription-test"
TENANT_ID_TEST_VALUE = "tenant-test"
CLIENT_ID_TEST_VALUE = "client-id-test"
CLIENT_SECRET_TEST_VALUE = "client-secret-test"
SUBSCRIPTION_ID_NEW_VALUE = "subscription-test-new"
CLIENT_SECRET_NEW_VALUE = "client-secret-test-new"


@pytest.mark.abort_on_fail
def test_build_and_deploy_charm(
    juju: jubilant.Juju, azure_auth_charm_path: Path, test_charm_path: Path
):
    """Tests building and deploying the integrator and the test charm, with proper statuses."""
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
    juju.config(
        APP_NAME,
        {"subscription-id": SUBSCRIPTION_ID_TEST_VALUE, "tenant-id": TENANT_ID_TEST_VALUE},
    )

    # Status should be blocked due to missing "credentials"
    status = juju.wait(
        lambda status: jubilant.all_blocked(status, APP_NAME),
    )
    assert status.apps[APP_NAME].app_status.message == "Missing parameters: ['credentials']"

    # Assert that configuring a secret that doesn't exist produces an error message
    # Create a secret and immediately remove it
    secret_uri = juju.add_secret("fake-secret", {"test-key": "test-value"})
    juju.remove_secret(secret_uri)
    juju.config(APP_NAME, {"credentials": secret_uri})
    juju.wait(jubilant.all_agents_idle)
    status = juju.wait(
        lambda status: jubilant.all_blocked(status, APP_NAME),
    )
    assert status.apps[APP_NAME].app_status.message == f"The secret '{secret_uri}' does not exist."

    # Add a secret but don't grant permission, so status should stay blocked
    secret_uri = juju.add_secret(SECRET_IDENTIFIER, {"client-id": CLIENT_ID_TEST_VALUE})
    juju.wait(jubilant.all_agents_idle)
    juju.config(APP_NAME, {"credentials": secret_uri})
    juju.wait(jubilant.all_agents_idle)
    status = juju.wait(lambda status: jubilant.all_blocked(status, APP_NAME))
    assert (
        status.apps[APP_NAME].app_status.message
        == f"Permission for secret '{secret_uri}' has not been granted."
    )
    juju.remove_secret(secret_uri)

    # Add a secret but don't provide all values for the secret, so status should stay blocked
    secret_uri = juju.add_secret(SECRET_IDENTIFIER, {"client-id": CLIENT_ID_TEST_VALUE})
    juju.grant_secret(secret_uri, APP_NAME)
    juju.config(APP_NAME, {"credentials": secret_uri})
    juju.wait(jubilant.all_agents_idle, delay=5.0)
    status = juju.wait(lambda status: jubilant.all_blocked(status, APP_NAME))
    assert (
        status.apps[APP_NAME].app_status.message
        == f"The key 'client-secret' was not found in secret '{secret_uri}'."
    )

    # All credentials have been provided, status should now be active
    secret_uri = juju.update_secret(
        SECRET_IDENTIFIER,
        {"client-id": CLIENT_ID_TEST_VALUE, "client-secret": CLIENT_SECRET_TEST_VALUE},
    )
    juju.wait(jubilant.all_agents_idle, delay=5.0)
    status = juju.wait(lambda status: jubilant.all_active(status, APP_NAME))


@pytest.mark.abort_on_fail
def test_relation_creation(juju: jubilant.Juju):
    """Relate charm and wait for the expected changes in status."""
    juju.integrate(APP_NAME, TEST_APP_NAME)
    juju.wait(jubilant.all_active)

    # Ensure data exists in the relation databag
    azure_credentials = get_application_data(juju, TEST_APP_NAME, RELATION_NAME)
    logger.debug(azure_credentials)

    assert "subscription-id" in azure_credentials
    assert "tenant-id" in azure_credentials
    assert "secret-extra" in azure_credentials

    assert azure_credentials["subscription-id"] == SUBSCRIPTION_ID_TEST_VALUE
    assert azure_credentials["tenant-id"] == TENANT_ID_TEST_VALUE

    secret_uri = azure_credentials["secret-extra"]
    secret_data = juju.show_secret(secret_uri, reveal=True)
    assert secret_data.content["client-id"] == CLIENT_ID_TEST_VALUE
    assert secret_data.content["client-secret"] == CLIENT_SECRET_TEST_VALUE

    # Ensure data exists in the requirer side
    result = juju.run(TEST_APP_UNIT_NAME, "get-azure-service-principal-info")
    assert result.results["subscription-id"] == SUBSCRIPTION_ID_TEST_VALUE
    assert result.results["tenant-id"] == TENANT_ID_TEST_VALUE
    assert result.results["client-id"] == CLIENT_ID_TEST_VALUE
    assert result.results["client-secret"] == CLIENT_SECRET_TEST_VALUE


@pytest.mark.abort_on_fail
def test_credentials_updated(juju: jubilant.Juju):
    """Tests updating the credentials and having the updates propagated to the relation."""
    # Change the value of the config
    juju.config(APP_NAME, {"subscription-id": SUBSCRIPTION_ID_NEW_VALUE})
    juju.wait(jubilant.all_active)

    # Ensure data exists in the relation databag
    azure_credentials = get_application_data(juju, TEST_APP_NAME, RELATION_NAME)
    assert azure_credentials["subscription-id"] == SUBSCRIPTION_ID_NEW_VALUE
    assert azure_credentials["tenant-id"] == TENANT_ID_TEST_VALUE

    # Ensure data exists in the requirer side
    result = juju.run(TEST_APP_UNIT_NAME, "get-azure-service-principal-info")
    assert result.results["subscription-id"] == SUBSCRIPTION_ID_NEW_VALUE
    assert result.results["tenant-id"] == TENANT_ID_TEST_VALUE

    # Change the value of the secret
    juju.update_secret(
        SECRET_IDENTIFIER,
        {"client-id": CLIENT_ID_TEST_VALUE, "client-secret": CLIENT_SECRET_NEW_VALUE},
    )
    juju.wait(jubilant.all_active)

    # Ensure data exists in the relation databag
    azure_credentials = get_application_data(juju, TEST_APP_NAME, RELATION_NAME)
    assert "subscription-id" in azure_credentials
    assert "tenant-id" in azure_credentials
    assert "secret-extra" in azure_credentials
    secret_uri = azure_credentials["secret-extra"]
    secret_data = juju.show_secret(secret_uri, reveal=True)
    assert secret_data.content["client-id"] == CLIENT_ID_TEST_VALUE
    assert secret_data.content["client-secret"] == CLIENT_SECRET_NEW_VALUE

    # Ensure data exists in the requirer side
    result = juju.run(TEST_APP_UNIT_NAME, "get-azure-service-principal-info")
    assert result.results["client-id"] == CLIENT_ID_TEST_VALUE
    assert result.results["client-secret"] == CLIENT_SECRET_NEW_VALUE


@pytest.mark.abort_on_fail
def test_relation_broken(juju: jubilant.Juju):
    """Removes relation and waits for the expected changes in status."""
    juju.remove_relation(APP_NAME, TEST_APP_NAME)

    juju.wait(lambda status: jubilant.all_active(status, APP_NAME), error=jubilant.any_error)

    # Test that charm's status changes to Blocked
    juju.wait(lambda status: jubilant.all_blocked(status, TEST_APP_NAME), error=jubilant.any_error)
