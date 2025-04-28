from fastapi import Request, status
from fastapi.exceptions import HTTPException
from typing import Any


# Custom exception for when establishing database connection fails
class DatabaseUnavailableException(HTTPException):
    def __init__(self, detail: Any = "Failed to connect to the database"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class InvalidXMLException(HTTPException):
    def __init__(self, detail: Any = "Invalid XML structure"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class UnrecognizedQuestionTypeException(HTTPException):
    def __init__(self, detail: Any = "Unrecognized question type encountered"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class AnswerMismatchException(HTTPException):
    def __init__(
        self, detail: Any = "Answers' type does not match the one expected by Question"
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class InvalidQuestionException(HTTPException):
    def __init__(self, detail: Any = "Invalid Question contents received"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class UnauthorizedException(HTTPException):
    def __init__(self, detail: Any = "Unauthorized access to protected resource"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class PublicKeyMissingException(HTTPException):
    def __init__(self, detail: Any = "Public Auth token not found. Set manually."):
        super().__init__(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=detail)


class UserGroupNotFoundException(HTTPException):
    def __init__(self, detail: Any = "Given User Group does not exist in database"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class RedisUnavailableException(HTTPException):
    def __init__(self, detail: Any = "Failed to connect to Redis"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )
