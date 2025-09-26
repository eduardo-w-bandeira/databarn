class DataBarnError(Exception):
    """Base class for all exceptions raised by DataBarn."""
    pass

class GrainTypeMismatchError(DataBarnError, TypeError):
    """Raised when an assignment to a grain is of the wrong type."""
    pass

class ConsistencyError(DataBarnError, ValueError):
    """Raised when an assignment to a grain fails due to constraint violations."""
    pass

class InvalidGrainLabelError(DataBarnError, NameError):
    """Raised when a variable name is invalid, and cannot be used as a grain label."""
    pass

class ComparisonNotSupportedError(DataBarnError, TypeError):
    """Raised when a comparison operation is not supported between two cobs."""
    pass