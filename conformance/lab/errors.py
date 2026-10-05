"""Lab errors. Every LabError is a non-result: the CLI exits 2."""


class LabError(Exception):
    exit_code = 2


class GateError(LabError):
    """A lifecycle or consent gate refused the command."""


class ScopeError(LabError):
    """SCOPE.json or a fault file is structurally invalid."""


class PinError(LabError):
    """A pinned commit or file hash did not match."""


class PlanError(LabError):
    """The run plan cannot be frozen or no longer matches."""


class EngineError(LabError):
    """An engine could not complete its procedure."""


class PackageError(LabError):
    """The package would leak data or is inconsistent."""


class GitHubError(LabError):
    """A gh or git call failed; lifecycle state is unchanged."""
