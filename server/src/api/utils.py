from src.types import UserGroupCD
from psycopg2.extensions import cursor
from src.database.crud import get_user_groups_all


async def existing_user_group_cd(user_group_cd: UserGroupCD, cursor: cursor) -> bool:
    user_groups = await get_user_groups_all(cursor=cursor)
    if user_group_cd in [user_group.user_group_cd for user_group in user_groups]:
        return True
    return False
