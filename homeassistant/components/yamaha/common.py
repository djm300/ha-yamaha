"""Shared Yamaha platform helpers."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import rxv
from .const import DISCOVER_TIMEOUT, DOMAIN
from .rxv import RXV

_LOGGER = logging.getLogger(__name__)

CONF_SOURCE_IGNORE = "source_ignore"
CONF_SOURCE_NAMES = "source_names"
CONF_ZONE_IGNORE = "zone_ignore"
CONF_ZONE_NAMES = "zone_names"

DEFAULT_NAME = "Yamaha Receiver"
MIN_VOLUME_DB = -80.0
RECEIVER_CONTEXTS = "receiver_contexts"

YAMAHA_CONFIG_SCHEMA = {
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_HOST): cv.string,
    vol.Optional(CONF_SOURCE_IGNORE, default=[]): vol.All(
        cv.ensure_list, [cv.string]
    ),
    vol.Optional(CONF_ZONE_IGNORE, default=[]): vol.All(
        cv.ensure_list, [cv.string]
    ),
    vol.Optional(CONF_SOURCE_NAMES, default={}): {cv.string: cv.string},
    vol.Optional(CONF_ZONE_NAMES, default={}): {cv.string: cv.string},
}


class YamahaConfigInfo:
    """Configuration Info for Yamaha Receivers."""

    def __init__(
        self, config: ConfigType, discovery_info: DiscoveryInfoType | None
    ) -> None:
        """Initialize the Configuration Info for Yamaha Receiver."""
        self.name = config.get(CONF_NAME)
        self.host = config.get(CONF_HOST)
        self.ctrl_url: str | None = f"http://{self.host}:80/YamahaRemoteControl/ctrl"
        self.source_ignore = config.get(CONF_SOURCE_IGNORE)
        self.source_names = config.get(CONF_SOURCE_NAMES)
        self.zone_ignore = config.get(CONF_ZONE_IGNORE)
        self.zone_names = config.get(CONF_ZONE_NAMES)
        self.from_discovery = False
        _LOGGER.debug("Discovery Info: %s", discovery_info)
        if discovery_info is not None:
            self.name = discovery_info.get("name")
            self.model = discovery_info.get("model_name")
            self.ctrl_url = discovery_info.get("control_url")
            self.desc_url = discovery_info.get("description_url")
            self.zone_ignore = []
            self.from_discovery = True


def discover_zone_controllers(config_info: YamahaConfigInfo) -> list[RXV]:
    """Discover list of zone controllers from configuration in the network."""
    _LOGGER.debug(
        "Starting Yamaha zone discovery: from_discovery=%s host=%s ctrl_url=%s name=%s",
        config_info.from_discovery,
        config_info.host,
        config_info.ctrl_url,
        config_info.name,
    )
    _LOGGER.debug("Loaded rxv module from %s", getattr(rxv, "__file__", "<unknown>"))
    if config_info.from_discovery:
        _LOGGER.debug("Discovery Zones")
        zones = rxv.RXV(
            config_info.ctrl_url,
            model_name=config_info.model,
            friendly_name=config_info.name,
            unit_desc_url=config_info.desc_url,
        ).zone_controllers()
    elif config_info.host is None:
        _LOGGER.debug("Config No Host Supplied Zones")
        zones = []
        for recv in rxv.find(DISCOVER_TIMEOUT):
            zones.extend(recv.zone_controllers())
    else:
        _LOGGER.debug("Config Zones")
        zones = rxv.RXV(config_info.ctrl_url, config_info.name).zone_controllers()

    _LOGGER.debug("Returned _discover zones: %s", zones)
    _LOGGER.debug(
        "Zone discovery returned %d controllers: %s",
        len(zones),
        [zone.zone for zone in zones],
    )
    return zones


def make_discovery_payload(
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None,
    receiver_id: str,
) -> dict[str, object]:
    """Create payload for loading Yamaha sibling platforms."""
    return {
        "receiver_id": receiver_id,
        "config": dict(config),
        "discovery_info": dict(discovery_info) if discovery_info is not None else None,
    }


def receiver_id_for(config_info: YamahaConfigInfo) -> str:
    """Build a stable key for sharing Yamaha zone controllers."""
    return config_info.ctrl_url or config_info.host or config_info.name or DEFAULT_NAME


def store_receiver_context(
    hass: HomeAssistant, config_info: YamahaConfigInfo, zone_ctrls: list[RXV]
) -> str:
    """Store shared Yamaha controller state for sibling platforms."""
    receiver_id = receiver_id_for(config_info)
    hass.data.setdefault(DOMAIN, {})[RECEIVER_CONTEXTS] = hass.data.setdefault(
        DOMAIN, {}
    ).get(RECEIVER_CONTEXTS, {})
    hass.data[DOMAIN][RECEIVER_CONTEXTS][receiver_id] = {
        "config_info": config_info,
        "zone_ctrls": zone_ctrls,
    }
    return receiver_id


def get_receiver_context(
    hass: HomeAssistant, receiver_id: str
) -> dict[str, YamahaConfigInfo | list[RXV]] | None:
    """Return shared Yamaha controller state for sibling platforms."""
    return hass.data.get(DOMAIN, {}).get(RECEIVER_CONTEXTS, {}).get(receiver_id)


def zone_display_name(
    base_name: str, zone: str, zone_names: dict[str, str] | None = None
) -> str:
    """Return the display name for a Yamaha zone."""
    zone_names = zone_names or {}
    zone_name = zone_names.get(zone, zone)
    if zone_name == "Main_Zone":
        return base_name
    return f"{base_name} {zone_name.replace('_', ' ')}"
