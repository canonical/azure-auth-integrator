# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Constants to be used in the charm code."""

AZURE_SERVICE_PRINCIPAL_RELATION_NAME = "azure-service-principal-credentials"

AZURE_SERVICE_PRINCIPAL_MANDATORY_OPTIONS = [
    "subscription-id",
    "tenant-id",
    "credentials",
]
