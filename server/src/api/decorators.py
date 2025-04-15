from fastapi import Query, HTTPException, Depends
from functools import wraps
from inspect import signature, Parameter
from typing import Optional, Callable, Any


def protected(token_name: str = "authToken"):
    def decorator(func: Callable) -> Callable:
        # Create dependency to check for the token
        def check_token(auth_token: Optional[str] = Query(None, alias=token_name)):
            if auth_token is None:
                raise HTTPException(
                    status_code=401,
                    detail=f"Missing {token_name} query parameter"
                )
            # Add token validation logic here if needed
            return auth_token

        # Modify function signature to include auth_token dependency
        sig = signature(func)
        parameters = list(sig.parameters.values())
        
        new_parameters = [
            Parameter(
                name="auth_token",
                kind=Parameter.KEYWORD_ONLY,
                default=Depends(check_token)
            )
        ] + parameters
        
        new_sig = sig.replace(parameters=new_parameters)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Remove auth_token before calling original function
            kwargs.pop("auth_token", None)
            return await func(*args, **kwargs)
        
        wrapper.__signature__ = new_sig
        return wrapper
    return decorator