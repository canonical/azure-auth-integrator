# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Definition of model classes."""

from dataclasses import dataclass


@dataclass
class AzureServicePrincipalInfo:
    """Azure service principal parameters."""
    subscription_id: str = ""
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""

    def __post_init__(self):
        """Clean up data immediately after initialization."""
        self.subscription_id = self.subscription_id or ""
        self.tenant_id = self.tenant_id or ""
        self.client_id = self.client_id or ""
        self.client_secret = self.client_secret or ""

    def to_dict(self) -> dict:
        return {
            "subscription-id": self.subscription_id,
            "tenant-id": self.tenant_id,
            "client-id": self.client_id,
            "client-secret": self.client_secret,
        }
