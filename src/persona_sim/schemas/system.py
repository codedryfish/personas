from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for health checks."""

    status: str = Field(default="ok", description="Service liveness indicator.")
    environment: str = Field(default="local", description="Deployment environment.")
    version: str = Field(default="0.1.0", description="Application version.")
