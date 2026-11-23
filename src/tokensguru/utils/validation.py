"""Input checks shared across the package."""


def require_text(text: object) -> None:
    if not isinstance(text, str):
        hint = " (use its .optimized_text)" if hasattr(text, "optimized_text") else ""
        raise TypeError(f"text must be a str, not {type(text).__name__}{hint}")
