# app/shared/exceptions.py
"""Custom exceptions for the application."""


class ProphecyError(Exception):
    """Base exception for all application errors."""

    pass


class ConfigurationError(ProphecyError):
    """Raised when configuration is invalid or missing."""

    pass


class ExternalAPIError(ProphecyError):
    """Raised when an external API call fails."""

    pass


class KalshiAPIError(ExternalAPIError):
    """Raised when Kalshi API call fails."""

    pass


class KalshiAuthenticationError(KalshiAPIError):
    """Raised when Kalshi authentication fails."""

    pass


class KalshiMarketNotFoundError(KalshiAPIError):
    """Raised when Kalshi market is not found."""

    pass


class KalshiEventNotFoundError(KalshiAPIError):
    """Raised when Kalshi event is not found."""

    pass


class TavilyAPIError(ExternalAPIError):
    """Raised when Tavily API call fails."""

    pass


class OpenAIAPIError(ExternalAPIError):
    """Raised when OpenAI API call fails."""

    pass


class DatabaseError(ProphecyError):
    """Raised when database operation fails."""

    pass


class ValidationError(ProphecyError):
    """Raised when data validation fails."""

    pass


class UnsupportedVenueError(ValidationError):
    """Raised when URL host is not supported."""


class VenueUrlParseError(ValidationError):
    """Raised when a supported venue URL cannot be parsed."""


class MarketNotFoundError(ExternalAPIError):
    """Raised when a venue market cannot be found."""


class EventNotFoundError(ExternalAPIError):
    """Raised when a venue event cannot be found."""
