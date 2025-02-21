import logging
import json
import aiohttp
import async_timeout

from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import DOMAIN, CONF_STATION_ID, ENDOLLA_URL

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Endolla integration from a config entry."""
    station_id = entry.data[CONF_STATION_ID]

    coordinator = EndollaCoordinator(hass, station_id=station_id)

    # Store the coordinator so sensor.py can access it
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # First fetch immediately
    await coordinator.async_config_entry_first_refresh()

    # Forward to sensor platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

class EndollaCoordinator(DataUpdateCoordinator):
    """Fetch Endolla data for a single station, keep it updated in HA."""

    def __init__(self, hass: HomeAssistant, station_id: str) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Endolla Station {station_id}",
            update_interval=SCAN_INTERVAL,
        )
        self.station_id = station_id

    async def _async_update_data(self):
        """Fetch data from the Endolla open data endpoint and parse out the station."""
        try:
            async with async_timeout.timeout(15):
                async with aiohttp.ClientSession() as session:
                    async with session.get(ENDOLLA_URL) as resp:
                        resp.raise_for_status()
                        text = await resp.text()
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

        # Parse JSON
        try:
            all_data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise UpdateFailed(f"Error parsing JSON: {exc}") from exc

        station_data = self._find_station_data(all_data, self.station_id)
        if not station_data:
            _LOGGER.warning("Station %s not found in Endolla data", self.station_id)
            return {}

        return station_data

    def _find_station_data(self, all_data, station_id):
        """Helper to locate the specified station_id in the Endolla JSON."""
        for location in all_data.get("locations", []):
            for station in location.get("stations", []):
                if station.get("id") == station_id:
                    return station
        return {}