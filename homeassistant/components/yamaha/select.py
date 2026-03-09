"""Select entities for Yamaha Receivers."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
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
    """Set up Yamaha input selects."""
    if discovery_info is None:
        return

    receiver_id = discovery_info.get("receiver_id")
    if receiver_id is None:
        return

    receiver_context = get_receiver_context(hass, receiver_id)
    if receiver_context is None:
        _LOGGER.debug("Missing Yamaha receiver context for select platform: %s", receiver_id)
        return

    config_info = receiver_context["config_info"]
    zone_ctrls = receiver_context["zone_ctrls"]

    main_zone = next((z for z in zone_ctrls if z.zone == "Main_Zone"), None)
    if main_zone is None:
        return

    assert config_info.name
    entity = YamahaInputSelect(
        config_info.name,
        main_zone,
        config_info.source_ignore,
        config_info.source_names,
    )
    _LOGGER.debug("Adding Yamaha select for %s: %s", config_info.name, entity.name)
    async_add_entities([entity])


class YamahaInputSelect(SelectEntity):
    """Input source select for a Yamaha receiver."""

    def __init__(
        self,
        name: str,
        zctrl: RXV,
        source_ignore: list[str] | None,
        source_names: dict[str, str] | None,
    ) -> None:
        self._name = name
        self.zctrl = zctrl
        self._source_ignore = source_ignore or []
        self._source_names = source_names or {}
        self._reverse_mapping = {
            alias: source for source, alias in self._source_names.items()
        }
        self._attr_options = []
        self._attr_current_option = None
        self._attr_available = True
        if zctrl.serial_number is not None:
            self._attr_unique_id = f"{zctrl.serial_number}_input_select"

    @property
    def name(self) -> str:
        return f"{self._name} Input"

    def _select_input(self, option: str) -> None:
        self.zctrl.input = self._reverse_mapping.get(option, option)
        self._attr_current_option = option

    async def async_select_option(self, option: str) -> None:
        await self.hass.async_add_executor_job(self._select_input, option)
        self.async_write_ha_state()

    def update(self) -> None:
        sources = sorted(
            self._source_names.get(source, source)
            for source in self.zctrl.inputs()
            if source not in self._source_ignore
        )
        current_source = self.zctrl.input
        current_option = self._source_names.get(current_source, current_source)
        if current_option not in sources:
            sources.append(current_option)
            sources.sort()
        self._attr_options = sources
        self._attr_current_option = current_option
        self._attr_available = True
