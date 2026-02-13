# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Base utilities exposing common functionalities for all Events classes."""

from ops import Object, StatusBase
from ops.model import ActiveStatus, BlockedStatus

from constants import AZURE_SERVICE_PRINCIPAL_MANDATORY_OPTIONS
from utils.logging import WithLogging
from utils.secrets import decode_secret_key


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
            decode_secret_key(model, charm_config.get("credentials"))
        except Exception as e:
            self.logger.warning(f"Error in decoding secret: {e}")
            return BlockedStatus(str(e))

        return ActiveStatus()
