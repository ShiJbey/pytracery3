"""Tracery modifiers."""


def replace(text: str, *params: str) -> str:
    """Replace text with a given string.

    Parameters
    ----------
    text
        The text to modify
    *params
        Additional parameters for the modifier

    Returns
    -------
    str
        A modified version of the text
    """
    return text.replace(params[0], params[1])


def capitalize_all(text: str, *params: str) -> str:
    """Convert text to title case, capitalizing the first letter of all words.

    Parameters
    ----------
    text
        The text to modify
    *params
        Additional parameters for the modifier

    Returns
    -------
    str
        A modified version of the text
    """
    return text.title()


def capitalize(text: str, *params: str) -> str:
    """Capitalize the first letter.

    Parameters
    ----------
    text
        The text to modify
    *params
        Additional parameters for the modifier

    Returns
    -------
    str
        A modified version of the text
    """
    return text[0].upper() + text[1:]


def a(text: str, *params: str) -> str:
    """Add proper (a/an) article before noun.

    Parameters
    ----------
    text
        The text to modify
    *params
        Additional parameters for the modifier

    Returns
    -------
    str
        A modified version of the text
    """
    if len(text) > 0:
        if text[0] in "uU":
            if len(text) > 2:
                if text[2] in "iI":
                    return "a " + text
        if text[0] in "aeiouAEIOU":
            return "an " + text
    return "a " + text


def first_s(text: str, *params: str) -> str:
    """Pluralize first word of text.

    Parameters
    ----------
    text
        The text to modify
    *params
        Additional parameters for the modifier

    Returns
    -------
    str
        A modified version of the text
    """
    text2 = text.split(" ")
    return " ".join([s(text2[0])] + text2[1:])


def s(text: str, *params: str) -> str:
    """Pluralize text.

    Parameters
    ----------
    text
        The text to modify
    *params
        Additional parameters for the modifier

    Returns
    -------
    str
        A modified version of the text
    """
    if text[-1] in "shxSHX":
        return text + "es"
    elif text[-1] in "yY":
        if text[-2] not in "aeiouAEIOU":
            return text[:-1] + "ies"
        else:
            return text + "s"
    else:
        return text + "s"


def ed(text: str, *params: str) -> str:
    """Convert text to past-tense.

    Parameters
    ----------
    text
        The text to modify
    *params
        Additional parameters for the modifier

    Returns
    -------
    str
        A modified version of the text
    """
    if text[-1] in "eE":
        return text + "d"

    elif text[-1] in "yY":
        if text[-2] not in "aeiouAEIOU":
            return text[:-1] + "ied"

    return text + "ed"


def uppercase(text: str, *params: str) -> str:
    """Convert text to uppercase.

    Parameters
    ----------
    text
        The text to modify
    *params
        Additional parameters for the modifier

    Returns
    -------
    str
        A modified version of the text
    """
    return text.upper()


def lowercase(text: str, *params: str) -> str:
    """Convert text to lowercase.

    Parameters
    ----------
    text
        The text to modify
    *params
        Additional parameters for the modifier

    Returns
    -------
    str
        A modified version of the text
    """
    return text.lower()


base_english = {
    "replace": replace,
    "capitalizeAll": capitalize_all,
    "capitalize": capitalize,
    "a": a,
    "firstS": first_s,
    "s": s,
    "ed": ed,
    "uppercase": uppercase,
    "lowercase": lowercase,
}
"""Modifier functions packaged in a dictionary similar to JS implementation."""
