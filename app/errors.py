class ETLError(Exception):
    """Base error for the WHO ETL pipeline."""


class ETLConfigurationError(ETLError):
    """Missing or invalid configuration (e.g. DATABASE_URL)."""


class ETLExtractError(ETLError):
    """Failed to fetch data from the upstream API."""


class ETLLoadError(ETLError):
    """Failed to persist transformed records to the database."""


class ETLStateError(ETLError):
    """Failed to read or write pipeline checkpoint state."""
