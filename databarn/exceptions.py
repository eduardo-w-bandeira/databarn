class GrainTypeMismatchError(TypeError):
    """Raised when an assignment to a grain is of the wrong type."""
    pass

class ConsistencyError(ValueError):
    """Raised when an assignment to a grain fails due to constraint violations."""
    pass

class CobAttributeNameError(NameError):
    """Raised when a variable name is invalid, and cannot be used as a grain label."""
    pass

class CobComparibilityError(TypeError):
    """Raised when a comparison operation is not supported between two cobs."""
    pass