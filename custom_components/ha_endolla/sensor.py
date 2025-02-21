import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import DOMAIN, CONF_STATION_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up Endolla sensors (one per port) for this config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    station_id = coordinator.station_id

    # Wait until first refresh is done (coordinator.data is not empty)
    if not coordinator.data:
        # If for some reason data is empty, we wait until next update.
        _LOGGER.warning("No station data yet. Entities will show up after first fetch.")
        # We'll still set up the platform with an empty list, then next update
        # will cause them to refresh if we create them dynamically.
        # For a simpler approach, do a guard or do an immediate update again.

    station_data = coordinator.data  # This will be a dict from Endolla
    ports = station_data.get("ports", [])

    entities = []
    for port in ports:
        port_id = port.get("id")
        entities.append(EndollaPortSensor(coordinator, station_id, port_id))

    async_add_entities(entities, update_before_add=True)


class EndollaPortSensor(CoordinatorEntity, SensorEntity):
    """A sensor representing a single Endolla port's status."""

    def __init__(self, coordinator, station_id, port_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._station_id = station_id
        self._port_id = port_id

        # Unique ID for each station+port
        self._attr_unique_id = f"endolla_{station_id}_{port_id}"

        # Name that appears in HA UI
        self._attr_name = f"Endolla {station_id} Port {port_id}"

        # Optionally define a device_info if you want them grouped under a device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, station_id)},
            name=f"Endolla Station {station_id}",
            manufacturer="Endolla Barcelona",
        )

    @property
    def native_value(self):
        """
        Return the sensor's main state.
        For ports, likely 'AVAILABLE', 'IN_USE', 'OUT_OF_ORDER', etc.
        """
        station_data = self.coordinator.data
        if not station_data:
            return None

        # Find the port data
        port_list = station_data.get("ports", [])
        for port in port_list:
            if port.get("id") == self._port_id:
                status_obj = (port.get("port_status") or [{}])[0]
                return status_obj.get("status", "UNKNOWN")
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes, e.g. last_updated."""
        station_data = self.coordinator.data
        if not station_data:
            return {}

        port_list = station_data.get("ports", [])
        for port in port_list:
            if port.get("id") == self._port_id:
                return {
                    "last_updated": port.get("last_updated", "")
                }
        return {}

    @property
    def icon(self):
        """Set a custom icon if desired, else fallback or use default sensor icon."""
        # Simple example: different icon if in use vs available
        state = self.native_value
        if state == "IN_USE":
            return "mdi:ev-station"
        elif state == "OUT_OF_ORDER":
            return "mdi:alert"
        return "mdi:power-plug"

    # The CoordinatorEntity base class automatically calls self.async_write_ha_state()
