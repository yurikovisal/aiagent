from pydantic import BaseModel, Field


class DependencyCheck(BaseModel):
    status: str
    optional: bool = False
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    env: str
    gpu_enabled: bool = False
    dependencies: dict[str, DependencyCheck] = Field(default_factory=dict)
