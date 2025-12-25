"""Domain-specific exceptions for simulation services."""

from __future__ import annotations


class SimulationError(Exception):
    """Base exception for simulation domain issues."""


class ValidationError(SimulationError):
    """Raised when provided inputs are invalid or incomplete."""


class NotFoundError(SimulationError):
    """Raised when requested simulation artifacts cannot be located."""


class RunFailedError(SimulationError):
    """Raised when a simulation run cannot be completed successfully."""
