from typing import Annotated, Literal
from pydantic import Field


UserGroupCD = Annotated[str, Field(..., min_length=1, max_length=100)]
LevelCD = Annotated[str, Field(..., min_length=1, max_length=100)]
PEM = Annotated[str, Field(..., min_length=1)]
InferenceScoreVal = Annotated[int, Field(..., ge=1, le=5)]
BinaryInferenceScoreVal = Literal[1, 5]
ModelTemperature = Annotated[float, Field(..., gt=0.0, le=1.0)]

Language = Literal["ru", "en"]
BaseName = Annotated[str, Field(..., min_length=1)]
BaseDesc = Annotated[str, Field(..., min_length=1)]
