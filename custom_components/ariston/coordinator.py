"""Coordinator class for Ariston module."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging

from ariston.base_device import AristonBaseDevice
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Seconds to wait after the 1st, 2nd and later consecutive failures (never
# shorter than the scan interval), so a struggling cloud isn't hammered.
BACKOFF_SECONDS = (300, 600, 1800)


class DeviceDataUpdateCoordinator(DataUpdateCoordinator):
    """Manages polling for state changes from the device."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: AristonBaseDevice,
        scan_interval_seconds: int,
        coordinator_name: str,
        async_update_state: Callable,
    ) -> None:
        """Initialize the data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{device.name}-{coordinator_name}",
            update_interval=timedelta(seconds=scan_interval_seconds),
            update_method=self._async_update_with_backoff,
        )

        self.device = device
        self._scan_interval = timedelta(seconds=scan_interval_seconds)
        self._update_state = async_update_state
        self._failures = 0

    async def _async_update_with_backoff(self):
        """Run the update; after failures, poll less often until one works."""
        try:
            data = await self._update_state()
        except Exception:
            self._failures += 1
            wait = BACKOFF_SECONDS[min(self._failures, len(BACKOFF_SECONDS)) - 1]
            self.update_interval = max(self._scan_interval, timedelta(seconds=wait))
            _LOGGER.debug(
                "%s failed %d time(s), next update in %s",
                self.name, self._failures, self.update_interval,
            )
            raise
        if self._failures:
            _LOGGER.info("%s recovered after %d failure(s)", self.name, self._failures)
            self._failures = 0
            self.update_interval = self._scan_interval
        return data
