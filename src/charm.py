#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""A charm for integrating Azure service principal credentials to a charmed application."""

import logging

import ops

from core.context import Context
from events.lifecycle import LifecycleEvents

logger = logging.getLogger(__name__)


class AzureAuthIntegratorCharm(ops.charm.CharmBase):
    """The main class for the charm."""

    def __init__(self, *args) -> None:
        super().__init__(*args)

        # Context
        self.context = Context(model=self.model, config=self.config)

        # Event Handlers
        self.lifecycle_events = LifecycleEvents(self, self.context)

        self.framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)
        self.framework.observe(self.on.collect_app_status, self._on_collect_app_status)

    def _on_collect_unit_status(self, event: ops.CollectStatusEvent) -> None:
        """Set the status of the unit.

        This must be the only place in the codebase where we set the unit status.

        The priority order is as follows:
        - domain logic
        - plain active status
        """
        for status in self._collect_domain_statuses():
            event.add_status(status)

        event.add_status(ops.model.ActiveStatus())

    def _on_collect_app_status(self, event: ops.CollectStatusEvent) -> None:
        """Set the status of the app.

        This must be the only place in the codebase where we set the app status.
        """
        for status in self._collect_domain_statuses():
            event.add_status(status)

        event.add_status(ops.model.ActiveStatus())

    def _collect_domain_statuses(self) -> list[ops.StatusBase]:
        """Return a list of each component status of the charm."""
        statuses: list[ops.StatusBase] = []

        statuses.append(
            self.lifecycle_events.get_app_status(
                self.lifecycle_events.charm.model,
                self.lifecycle_events.charm.config,
            )
        )

        return statuses


if __name__ == "__main__":
    ops.main(AzureAuthIntegratorCharm)
