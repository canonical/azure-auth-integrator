"""Utility functions related to secrets."""

import logging
from typing import Optional

import ops
import ops.charm
import ops.framework
import ops.lib
import ops.main
import ops.model

logger = logging.getLogger(__name__)


def decode_secret_key(model: ops.Model, secret_id: str) -> Optional[str]:
    """Decode the secret with a given secret_id and return "client-secret" in plaintext value.

    Args:
        model: juju model to operate in
        secret_id (str): The ID (URI) of the secret that contains the secret key

    Raises:
        ops.model.SecretNotFoundError: When either the secret does not exist or the secret
            does not have client-secret in its content.
        ops.model.ModelError: When the permission to access the secret has not been granted
            yet.

    Returns:
        Optional[str]: The value of client-secret in plain text.
    """
    try:
        secret_content = model.get_secret(id=secret_id).get_content(refresh=True)

        if not secret_content.get("client-secret"):
            raise ValueError(f"The field 'client-secret' was not found in the secret '{secret_id}'.")
        return secret_content["client-secret"]
    except ops.model.SecretNotFoundError:
        raise ops.model.SecretNotFoundError(f"The secret '{secret_id}' does not exist.")
    except ValueError as ve:
        raise ops.model.SecretNotFoundError(ve)
    except ops.model.ModelError as me:
        if "permission denied" in str(me):
            raise ops.model.ModelError(
                f"Permission for secret '{secret_id}' has not been granted."
            )
        raise
