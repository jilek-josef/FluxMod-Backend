from datetime import datetime
from collections import defaultdict

from api2.database.mongo import MongoDB

db = MongoDB()
warns = db.collection("warns")


def add_warn(guild_id: int, user_id: int, moderator_id: int, reason: str):

    warn = {
        "guild_id": guild_id,
        "user_id": user_id,
        "moderator_id": moderator_id,
        "reason": reason,
        "timestamp": datetime.utcnow(),
    }

    warns.insert_one(warn)


def get_user_warns(guild_id: int, user_id: int):

    return list(warns.find({"guild_id": guild_id, "user_id": user_id}))


def remove_warn(guild_id: int, user_id: int, warn_id):

    warns.delete_one({"guild_id": guild_id, "user_id": user_id, "_id": warn_id})


def clear_user_warns(guild_id: int, user_id: int):

    warns.delete_many({"guild_id": guild_id, "user_id": user_id})


def remove_warn_by_index(guild_id: int, user_id: int, index: int) -> bool:

    user_warns = list(
        warns.find({"guild_id": guild_id, "user_id": user_id}).sort("timestamp", 1)
    )

    if not (0 <= index < len(user_warns)):
        return False

    warn_id = user_warns[index].get("_id")

    if warn_id is None:
        return False

    result = warns.delete_one({"_id": warn_id})

    return result.deleted_count > 0


def get_warns_grouped_by_guild_user() -> dict[int, dict[int, list[dict]]]:

    grouped: dict[int, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))

    for warn in warns.find(
        {},
        {
            "_id": 1,
            "guild_id": 1,
            "user_id": 1,
            "reason": 1,
            "moderator_id": 1,
            "timestamp": 1,
        },
    ):
        guild_id = warn.get("guild_id")
        user_id = warn.get("user_id")

        if not isinstance(guild_id, int) or not isinstance(user_id, int):
            continue

        grouped[guild_id][user_id].append(warn)

    return {gid: dict(users) for gid, users in grouped.items()}


def delete_warns_older_than(cutoff: datetime) -> int:

    result = warns.delete_many({"timestamp": {"$lt": cutoff}})

    return result.deleted_count
