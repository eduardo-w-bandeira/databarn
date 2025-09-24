class GrainTypeMismatchError(TypeError):
    """Raised when an assignment to a sprout is of the wrong type."""
    pass

class ConsistencyError(ValueError):
    """Raised when an assignment to a sprout fails due to constraint violations."""
    pass

class CobAttributeNameError(NameError):
    """Raised when a variable name is invalid, and cannot be used as a sprout label."""
    pass

class CobComparibilityError(TypeError):
    """Raised when a comparison operation is not supported between two cobs."""
    pass