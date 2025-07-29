# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Base utilities exposing common functionalities for all Events classes."""

from ops import Model, Object, StatusBase
from ops.model import ActiveStatus, BlockedStatus, ModelError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from constants import AZURE_SERVICE_PRINCIPAL_MANDATORY_OPTIONS
from utils.logging import WithLogging
from utils.secrets import decode_secret_key


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry=retry_if_exception_type(ModelError),
    reraise=True,
)
def decode_secret_key_with_retry(model: Model, secret_id: str):
    """Try to decode the secret key, retry for 3 times before failing."""
    return decode_secret_key(model, secret_id)


class BaseEventHandler(Object, WithLogging):
    """Base class for all Event Handler classes."""

    def get_app_status(self, model, charm_config) -> StatusBase:
        """Return the status of the charm."""
        missing_options = []
        for config_option in AZURE_SERVICE_PRINCIPAL_MANDATORY_OPTIONS:
            if not charm_config.get(config_option):
                missing_options.append(config_option)
        if missing_options:
            self.logger.warning(f"Missing parameters: {missing_options}")
            return BlockedStatus(f"Missing parameters: {missing_options}")
        try:
            decode_secret_key_with_retry(model, charm_config.get("credentials"))
        except Exception as e:
            self.logger.warning(f"Error in decoding secret: {e}")
            return BlockedStatus(str(e))

        return ActiveStatus()
