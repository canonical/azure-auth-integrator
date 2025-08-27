# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Definition of model classes."""

from dataclasses import dataclass


@dataclass
class AzureServicePrincipalInfo:
    """Azure service principal parameters."""

    storage_account: str
    container: str
    subscription_id: str
    tenant_id: str
    client_id: str
    client_secret: str
    path: str = ""

    def to_dict(self) -> dict:
        """Return the Azure service principal parameters as a dictionary."""
        data = {
            "subscription-id": self.subscription_id,
            "tenant-id": self.tenant_id,
            "client-id": self.client_id,
            "client-secret": self.client_secret,
            "storage-account": self.storage_account,
            "container": self.container,
            "path": self.path,
        }
        return data
