"""Pydantic models for MCP tool return types and outputSchema generation."""

from pydantic import BaseModel, Field


class ConversionResult(BaseModel):
    """Result of a single unit conversion."""

    original_value: float
    original_unit: str
    converted_value: float
    converted_unit: str
    conversion_type: str


class BatchItemResult(BaseModel):
    """Result of one conversion within a batch request."""

    request_id: str
    success: bool
    original_value: float | None = None
    original_unit: str | None = None
    converted_value: float | None = None
    converted_unit: str | None = None
    conversion_type: str | None = None
    error: str | None = None


class BatchSummary(BaseModel):
    """Aggregate counts for a batch conversion request."""

    total_requests: int
    successful_conversions: int
    failed_conversions: int


class BatchConversionResult(BaseModel):
    """Structured response from convert_batch."""

    batch_results: list[BatchItemResult]
    summary: BatchSummary


class SupportedUnitsResponse(BaseModel):
    """Supported units for one or all conversion types."""

    angle: list[str] | None = None
    area: list[str] | None = None
    computer_data: list[str] | None = None
    density: list[str] | None = None
    energy: list[str] | None = None
    force: list[str] | None = None
    temperature: list[str] | None = None
    length: list[str] | None = None
    mass: list[str] | None = None
    power: list[str] | None = None
    pressure: list[str] | None = None
    speed: list[str] | None = None
    time: list[str] | None = None
    volume: list[str] | None = Field(default=None)
