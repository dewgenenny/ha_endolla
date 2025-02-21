from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN, CONF_STATION_ID

class EndollaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Endolla integration."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            station_id = user_input[CONF_STATION_ID]

            # Optional: Validate station_id (e.g. require numeric)
            # if not station_id.isdigit():
            #     errors["base"] = "invalid_station_id"

            if not errors:
                # Create the config entry
                return self.async_create_entry(
                    title=f"Endolla Station {station_id}",
                    data=user_input
                )

        data_schema = vol.Schema({
            vol.Required(CONF_STATION_ID): str
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )
