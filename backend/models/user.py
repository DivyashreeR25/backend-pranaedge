from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional

import re

class HealthProfile(BaseModel):
    name: str
    age: int
    weight: float
    fitness_goal: str
    health_conditions: List[str]
    sleep_quality: int
    stress_level: int
    email: EmailStr
    password: str

    @field_validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")

        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str  


class ProfileResponse(BaseModel):
    user_id: str
    message: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    name: str