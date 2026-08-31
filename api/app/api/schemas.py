"""Request/response contracts for the routing endpoint."""

from pydantic import BaseModel, EmailStr, Field

from app.domain.departments import Department


class RouteRequest(BaseModel):
    email: EmailStr
    message: str = Field(min_length=1, max_length=4000)


class RouteResponse(BaseModel):
    department: Department
    department_email: str
    reasoning: str
    used_fallback: bool
