from __future__ import annotations

import uuid
from typing import List, Dict, Any
from datetime import datetime

from api2.database.guilds import (
    get_guild,
    get_all_guilds,
    create_guild,
    get_command_settings,
    update_command_settings,
    get_log_channel_id,
    set_log_channel_id,
)
from api2.database.automod import (
    get_rules,
    get_enabled_rules,
    get_rule,
    add_rule,
    update_rule_by_id,
    delete_rule_by_id,
    get_guild_id_by_rule_id,
)
from api2.database.warns import (
    add_warn,
    get_user_warns,
    remove_warn,
    clear_user_warns,
    remove_warn_by_index,
    get_warns_grouped_by_guild_user,
    delete_warns_older_than,
)


class DataWrapper:
    def __init__(self):

        self._automod_cache: Dict[int, List[dict]] = {}

    def list_guilds(self) -> list[dict[str, Any]]:
        """Return known guilds with computed rule counts for API responses."""
        guilds: list[dict[str, Any]] = []

        for guild in get_all_guilds():
            guild_id = guild.get("guild_id")
            if guild_id is None:
                continue

            rules = guild.get("automod_rules", [])
            command_settings = guild.get("command_settings", {})
            guilds.append(
                {
                    "id": str(guild_id),
                    "name": command_settings.get("name")
                    if isinstance(command_settings, dict)
                    else None,
                    "rule_count": len(rules) if isinstance(rules, list) else 0,
                }
            )

        return guilds

    def list_rules_for_guild(self, guild_id: str) -> list[dict[str, Any]]:
        """Return all stored rules for a guild id."""

        if not guild_id.isdigit():
            return []

        guild_id_int = int(guild_id)
        rules = get_rules(guild_id_int)

        return [{"guild_id": guild_id, **rule} for rule in rules]

    def create_rule(
        self, guild_id: str, normalized_rule_payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Create and persist a new rule for a guild."""

        guild_id_int = int(guild_id)
        if not get_guild(guild_id_int):
            create_guild(guild_id_int)

        keywords_value = normalized_rule_payload.get(
            "keywords", normalized_rule_payload.get("keyword", [])
        )
        if isinstance(keywords_value, str):
            keywords = [keywords_value.strip()] if keywords_value.strip() else []
        elif isinstance(keywords_value, list):
            keywords = [
                str(item).strip() for item in keywords_value if str(item).strip()
            ]
        else:
            keywords = []

        allowed_patterns_value = normalized_rule_payload.get(
            "allowed_patterns",
            normalized_rule_payload.get("allowed_keywords", []),
        )
        if isinstance(allowed_patterns_value, str):
            allowed_patterns = (
                [allowed_patterns_value.strip()]
                if allowed_patterns_value.strip()
                else []
            )
        elif isinstance(allowed_patterns_value, list):
            allowed_patterns = [
                str(item).strip()
                for item in allowed_patterns_value
                if str(item).strip()
            ]
        else:
            allowed_patterns = []

        rule_payload = {
            **normalized_rule_payload,
            "keywords": keywords,
            "allowed_patterns": allowed_patterns,
        }

        rule: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            **rule_payload,
        }

        add_rule(guild_id_int, rule)
        self._automod_cache.pop(guild_id_int, None)

        return {"guild_id": guild_id, **rule}

    def update_rule(
        self, rule_id: str, normalized_rule_payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update and persist a rule by id, returning the updated rule when found."""

        keywords_value = normalized_rule_payload.get(
            "keywords", normalized_rule_payload.get("keyword", [])
        )
        if isinstance(keywords_value, str):
            keywords = [keywords_value.strip()] if keywords_value.strip() else []
        elif isinstance(keywords_value, list):
            keywords = [
                str(item).strip() for item in keywords_value if str(item).strip()
            ]
        else:
            keywords = []

        allowed_patterns_value = normalized_rule_payload.get(
            "allowed_patterns",
            normalized_rule_payload.get("allowed_keywords", []),
        )
        if isinstance(allowed_patterns_value, str):
            allowed_patterns = (
                [allowed_patterns_value.strip()]
                if allowed_patterns_value.strip()
                else []
            )
        elif isinstance(allowed_patterns_value, list):
            allowed_patterns = [
                str(item).strip()
                for item in allowed_patterns_value
                if str(item).strip()
            ]
        else:
            allowed_patterns = []

        update_payload = {
            **normalized_rule_payload,
            "keywords": keywords,
            "allowed_patterns": allowed_patterns,
        }

        updated_rule = update_rule_by_id(rule_id, update_payload)
        if updated_rule is None:
            return None

        guild_id = updated_rule.get("guild_id")
        if isinstance(guild_id, str) and guild_id.isdigit():
            self._automod_cache.pop(int(guild_id), None)

        return updated_rule

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule by id and report whether a record was removed."""

        guild = get_guild_id_by_rule_id(rule_id)
        deleted = delete_rule_by_id(rule_id)
        if deleted and isinstance(guild, int):
            self._automod_cache.pop(guild, None)

        return deleted

    async def ensure_guild(self, guild_id: int):

        guild = get_guild(guild_id)

        if not guild:
            create_guild(guild_id)

    async def get_guild_data(self, guild_id: int) -> dict | None:

        return get_guild(guild_id)

    async def get_command_settings(self, guild_id: int) -> dict:

        return get_command_settings(guild_id)

    async def update_command_settings(self, guild_id: int, settings: dict):

        update_command_settings(guild_id, settings)

    async def get_automod_rules(self, guild_id: int) -> List[dict]:

        if guild_id in self._automod_cache:
            return self._automod_cache[guild_id]

        rules = get_rules(guild_id)

        self._automod_cache[guild_id] = rules

        return rules

    async def get_enabled_automod_rules(self, guild_id: int) -> List[dict]:

        return get_enabled_rules(guild_id)

    async def get_automod_rule(self, guild_id: int, rule_name: str) -> dict | None:

        return get_rule(guild_id, rule_name)

    async def invalidate_automod_cache(self, guild_id: int):

        self._automod_cache.pop(guild_id, None)

    async def add_warn(self, guild_id: int, user_id: int, mod_id: int, reason: str):

        add_warn(guild_id, user_id, mod_id, reason)

    async def get_warns(self, guild_id: int, user_id: int):

        return get_user_warns(guild_id, user_id)

    async def remove_warn(self, guild_id: int, user_id: int, warn_id):

        remove_warn(guild_id, user_id, warn_id)

    async def clear_warns(self, guild_id: int, user_id: int):

        clear_user_warns(guild_id, user_id)

    async def remove_warn_by_index(
        self, guild_id: int, user_id: int, index: int
    ) -> bool:

        return remove_warn_by_index(guild_id, user_id, index)

    async def get_warns_grouped(self) -> dict[int, dict[int, list[dict]]]:

        return get_warns_grouped_by_guild_user()

    async def delete_warns_older_than(self, cutoff: datetime) -> int:

        return delete_warns_older_than(cutoff)

    async def set_log_channel_id(self, guild_id: int, channel_id: int):

        set_log_channel_id(guild_id, channel_id)

    async def get_log_channel_id(self, guild_id: int) -> int | None:

        return get_log_channel_id(guild_id)
