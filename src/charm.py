#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""A charm for integrating Azure service principal credentials to a charmed application."""

import logging

import ops

from core.context import Context
from events.general import GeneralEvents

logger = logging.getLogger(__name__)


class AzureAuthIntegratorCharm(ops.charm.CharmBase):
    """The main class for the charm."""

    def __init__(self, *args) -> None:
        super().__init__(*args)

        # Context
        self.context = Context(model=self.model, config=self.config)

        # Event Handlers
        self.general_events = GeneralEvents(self, self.context)


if __name__ == "__main__":
    ops.main(AzureAuthIntegratorCharm)
