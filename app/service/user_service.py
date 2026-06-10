"""用户加载与密码校验（与 langchain-learn 相同测试账号）。"""

from dataclasses import dataclass

import bcrypt


@dataclass(frozen=True)
class User:
    user_id: str
    role: str
    password_hash: str


class UserService:
    DEFAULT_PASSWORD = "123456"

    def __init__(self) -> None:
        password_hash = self._hash_password(self.DEFAULT_PASSWORD)
        self._users: dict[str, User] = {
            "user1": User("user1", "USER", password_hash),
            "vip01": User("vip01", "VIP", password_hash),
            "admin01": User("admin01", "ADMIN", password_hash),
        }

    def find_by_user_id(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def authenticate(self, user_id: str, password: str) -> User | None:
        user = self.find_by_user_id(user_id)
        if user is None:
            return None
        if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            return None
        return user

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
