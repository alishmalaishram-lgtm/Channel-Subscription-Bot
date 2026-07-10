from datetime import datetime, timezone

from database.mongo import get_database

COLLECTION = "settings"


def settings_collection():
    return get_database()[COLLECTION]


async def get_setting(key: str):
    return await settings_collection().find_one(
        {"key": key}
    )


async def set_setting(key: str, value):
    await settings_collection().update_one(
        {"key": key},
        {
            "$set": {
                "value": value,
                "updated_at": datetime.now(timezone.utc),
            },
            "$setOnInsert": {
                "created_at": datetime.now(timezone.utc),
            },
        },
        upsert=True,
    )


async def delete_setting(key: str):
    await settings_collection().delete_one(
        {"key": key}
    )


async def get_all_settings():
    return await settings_collection().find().to_list(length=None)


async def maintenance_mode() -> bool:
    setting = await get_setting("maintenance_mode")

    if not setting:
        return False

    return bool(setting.get("value", False))
