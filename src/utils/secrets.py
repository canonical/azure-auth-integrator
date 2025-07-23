"""Utility functions related to secrets."""

import logging

import ops
import ops.charm
import ops.framework
import ops.lib
import ops.main
import ops.model

logger = logging.getLogger(__name__)


def decode_secret_key(model: ops.Model, secret_id: str) -> dict[str, str] | None:
    """Decode the secret with a given secret_id and return "client-id" and "client-secret".

    Args:
        model: juju model to operate in
        secret_id: The ID (URI) of the secret that contains the secret key

    Raises:
        ops.model.SecretNotFoundError: When either the secret does not exist or the secret
            does not have "client-secret" or "client-secret" in its content.
        ops.model.ModelError: When the permission to access the secret has not been granted
            yet.

    Returns:
        A dictionary containing the 'client-id' and 'client-secret'.
    """
    try:
        secret_content = model.get_secret(id=secret_id).get_content(refresh=True)

        for key in ["client-id", "client-secret"]:
            if not secret_content.get(key):
                raise ValueError(f"The field '{field}' was not found in secret '{secret_id}'.")

        return {
            "client-id": secret_content["client-id"],
            "client-secret": secret_content["client-secret"],
        }
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
