class SurveyGuardError(Exception):
    """Expected, user-facing SurveyGuard failure."""


class ConfigurationError(SurveyGuardError):
    pass


class DataValidationError(SurveyGuardError):
    pass


class MathematicalError(SurveyGuardError):
    pass