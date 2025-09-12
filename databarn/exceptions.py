
class VarNameError(Exception):
    """Raised when a variable name is invalid."""
    pass

class ConsistencyError(Exception):
    """Raised when an assignment to a grain fails due to constraint violations."""
    pass