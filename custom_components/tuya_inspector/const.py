"""Constants for the Tuya Device Inspector."""

DOMAIN = "tuya_inspector"

CONF_ACCESS_ID = "access_id"
CONF_ACCESS_SECRET = "access_secret"
CONF_DATA_CENTER = "data_center"
CONF_DEVICE_ID = "device_id"

SERVICE_EXPORT = "export"

# Tuya serves each account from exactly one data center, fixed by the country
# the app account was registered in.
DATA_CENTERS = {
    "us": "https://openapi.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}
DEFAULT_DATA_CENTER = "us"

TOKEN_PATH = "/v1.0/token?grant_type=1"

# 20 is the documented maximum; larger values are rejected with 40000904.
DEVICE_LIST_PATH = "/v2.0/cloud/thing/device?page_size=20"


def device_info_path(device_id: str) -> str:
    """The device record: product id, category, online state, activation."""
    return f"/v1.0/devices/{device_id}"


def model_path(device_id: str) -> str:
    """The things data model.

    This is the important one for adding support for a device: it lists every
    datapoint with its id, type, and the range or enum values it accepts.
    """
    return f"/v2.0/cloud/thing/{device_id}/model"


def specification_path(device_id: str) -> str:
    """Functions and status, keyed by code rather than datapoint id.

    Overlaps with the data model but presents things differently, and some
    firmware reports one and not the other, so both are collected.
    """
    return f"/v1.0/devices/{device_id}/specifications"


def properties_path(device_id: str) -> str:
    """Current datapoint values, including ids and timestamps."""
    return f"/v2.0/cloud/thing/{device_id}/shadow/properties"
