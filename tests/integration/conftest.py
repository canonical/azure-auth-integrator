import logging
from pathlib import Path

import jubilant
import pytest

WAIT_TIMEOUT = 10 * 60

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def juju(request: pytest.FixtureRequest):
    keep_models = bool(request.config.getoption("--keep-models"))
    model_name = request.config.getoption("--model")

    if model_name:
        juju_instance = jubilant.Juju(model=model_name)
        juju_instance.wait_timeout = WAIT_TIMEOUT
        juju_instance.model_config({"update-status-hook-interval": "60s"})

        yield juju_instance

        if request.session.testsfailed:
            log = juju_instance.debug_log(limit=30)
            print(log, end="")

    else:
        with jubilant.temp_model(keep=keep_models) as juju_instance:
            juju_instance.wait_timeout = WAIT_TIMEOUT
            juju_instance.model_config({"update-status-hook-interval": "60s"})

            yield juju_instance  # run the test

            if request.session.testsfailed:
                log = juju_instance.debug_log(limit=30)
                print(log, end="")


@pytest.fixture
def azure_auth_charm_path() -> Path:
    if not (path := next(iter(Path.cwd().glob("*.charm")), None)):
        raise FileNotFoundError("Could not find packed azure-auth-integrator charm.")

    return path


@pytest.fixture
def test_charm_path() -> Path:
    if not (
        path := next(
            iter((Path.cwd() / "tests/integration/test-charm-azure-service-principal").glob("*.charm")), None
        )
    ):
        raise FileNotFoundError("Could not find packed test charm.")

    return path
