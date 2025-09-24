class GrainTypeMismatchError(TypeError):
    """Raised when an assignment to a flake is of the wrong type."""
    pass

class ConsistencyError(ValueError):
    """Raised when an assignment to a flake fails due to constraint violations."""
    pass

class CobAttributeNameError(NameError):
    """Raised when a variable name is invalid, and cannot be used as a flake label."""
    pass

class CobComparibilityError(TypeError):
    """Raised when a comparison operation is not supported between two cobs."""
    pass