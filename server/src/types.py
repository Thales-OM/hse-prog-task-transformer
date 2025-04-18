from typing import Annotated, Optional
from pydantic import Field, BaseModel


UserGroupCD = Annotated[str, Field(..., min_length=1, max_length=100)]
LevelCD = Annotated[str, Field(..., min_length=1, max_length=100)]
PEM = Annotated[str, Field(..., min_length=1)]
InferenceScore = Annotated[int, Field(..., ge=1, le=10)]
ModelTemperature = Annotated[float, Field(..., gt=0.0, le=1.0)]
