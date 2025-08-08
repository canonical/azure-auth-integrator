import logging
from pathlib import Path

import jubilant
import pytest
import yaml

logger = logging.getLogger(__name__)


CHARM_METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
APP_NAME = CHARM_METADATA["name"]

TEST_CHARM_METADATA = yaml.safe_load(
    Path("./tests/integration/test-charm-azure-service-principal/metadata.yaml").read_text()
)
TEST_APP_NAME = TEST_CHARM_METADATA["name"]

def test_build_and_deploy_charm(juju: jubilant.Juju, azure_auth_charm_path: Path, test_charm_path: Path):
    """Test building and deploying the integrator and the test charm."""
    juju.deploy(
        azure_auth_charm_path,
        app=APP_NAME,
    )

    juju.config(
        APP_NAME,
        {"subscription-id": "subscription-test", "tenant-id": "tenant-test"}
    )

    secret_uri = juju.add_secret(
        "azure-secret",
        {"client-id": "id-test", "client-secret": "password-test"}
    )
    juju.grant_secret(
        secret_uri,
        APP_NAME
    )
    juju.config(
        APP_NAME,
        {"credentials": secret_uri}
    )

    juju.deploy(
        test_charm_path,
        app=TEST_APP_NAME,
    )

    juju.wait(
        lambda status: jubilant.all_active(status, APP_NAME),
        error=jubilant.any_error
    )

    juju.wait(
        lambda status: jubilant.all_blocked(status, TEST_APP_NAME),
        error=jubilant.any_error
    )

    
@pytest.mark.abort_on_fail
async def test_relation_creation(juju: jubilant.Juju):
    """Relate charm and wait for the expected changes in status."""

    juju.integrate(APP_NAME, TEST_APP_NAME)
    juju.wait(
        jubilant.all_active
    )
