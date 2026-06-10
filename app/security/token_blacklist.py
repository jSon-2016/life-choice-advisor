"""Access Token jti 黑名单（内存版）。"""

from datetime import datetime, timedelta


class AccessTokenBlacklist:
    def __init__(self) -> None:
        self._entries: dict[str, datetime] = {}

    def blacklist(self, jti: str, ttl_seconds: int) -> None:
        self._purge_expired()
        self._entries[jti] = datetime.now() + timedelta(seconds=max(ttl_seconds, 0))

    def is_blacklisted(self, jti: str) -> bool:
        self._purge_expired()
        return jti in self._entries

    def _purge_expired(self) -> None:
        now = datetime.now()
        self._entries = {jti: exp for jti, exp in self._entries.items() if exp > now}
