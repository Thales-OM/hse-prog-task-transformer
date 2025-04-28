from pydantic import BaseModel
from typing import Optional, Dict, Any
from src.types import Language


class UserSessionData(BaseModel):
    """Pydantic model defining the structure of user session data"""

    lang: Optional[Language] = None
