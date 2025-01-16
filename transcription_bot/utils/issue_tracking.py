_issues: list[str] = []


def report_issue(message: str) -> None:
    """Report an issue encountered during runtime."""
    _issues.append(message)


def get_issue_text() -> str:
    """Return the issues encountered during the runtime."""
    return "\n\n------\n\n".join(_issues)
