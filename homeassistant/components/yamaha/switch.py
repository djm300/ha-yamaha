"""Switch entities for Yamaha Receivers."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .common import get_receiver_context
from .rxv import RXV

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Yamaha switches."""
    if discovery_info is None:
        return

    receiver_id = discovery_info.get("receiver_id")
    if receiver_id is None:
        return

    receiver_context = get_receiver_context(hass, receiver_id)
    if receiver_context is None:
        _LOGGER.debug("Missing Yamaha receiver context for switch platform: %s", receiver_id)
        return

    config_info = receiver_context["config_info"]
    zone_ctrls = receiver_context["zone_ctrls"]

    main_zone = next((z for z in zone_ctrls if z.zone == "Main_Zone"), None)
    zone_b = next((z for z in zone_ctrls if z.zone == "Zone_B"), None)
    if main_zone is None:
        return

    assert config_info.name
    entities: list[SwitchEntity] = [
        YamahaReceiverPowerSwitch(config_info.name, main_zone),
        YamahaZoneSwitch(config_info.name, main_zone, "Zone A"),
    ]
    if zone_b is not None:
        entities.append(YamahaZoneSwitch(config_info.name, zone_b, "Zone B"))

    _LOGGER.debug(
        "Adding Yamaha switches for %s: %s",
        config_info.name,
        [entity.name for entity in entities],
    )
    async_add_entities(entities)


class YamahaReceiverPowerSwitch(SwitchEntity):
    """Power switch for the receiver itself."""

    def __init__(self, name: str, zctrl: RXV) -> None:
        self._name = name
        self.zctrl = zctrl
        self._attr_is_on = False
        self._attr_available = True
        if zctrl.serial_number is not None:
            self._attr_unique_id = f"{zctrl.serial_number}_receiver_power"

    @property
    def name(self) -> str:
        return f"{self._name} Power"

    @property
    def is_on(self) -> bool:
        return self._attr_is_on

    def _set_power(self, state: bool) -> None:
        self.zctrl.on = state
        self._attr_is_on = state

    async def async_turn_on(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._set_power, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._set_power, False)
        self.async_write_ha_state()

    def update(self) -> None:
        self._attr_is_on = self.zctrl.on
        self._attr_available = True


class YamahaZoneSwitch(SwitchEntity):
    """Switch for a Yamaha speaker zone."""

    def __init__(self, name: str, zctrl: RXV, zone_label: str) -> None:
        self._name = name
        self.zctrl = zctrl
        self._zone_label = zone_label
        self._attr_is_on = False
        self._attr_available = True
        if zctrl.serial_number is not None:
            zone_key = zone_label.lower().replace(" ", "_")
            self._attr_unique_id = f"{zctrl.serial_number}_{zone_key}"

    @property
    def name(self) -> str:
        return f"{self._name} {self._zone_label}"

    @property
    def is_on(self) -> bool:
        return self._attr_is_on

    def _set_enabled(self, state: bool) -> None:
        self.zctrl.enabled = state
        self._attr_is_on = state

    async def async_turn_on(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._set_enabled, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._set_enabled, False)
        self.async_write_ha_state()

    def update(self) -> None:
        self._attr_is_on = self.zctrl.enabled
        self._attr_available = True
