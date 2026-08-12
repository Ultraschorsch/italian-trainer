"""Regelbasierte Logik für Artikel (Genus) und Pluralbildung im Italienischen.
Deckt die produktiven Grundregeln ab; echte Ausnahmen werden über die
expliziten Felder 'plural' bzw. 'notes' am Lexeme hinterlegt."""

import re

_SPECIAL_MASC_START = re.compile(r"^(s[bcdfglmnpqrtv]|z|gn|ps|pn|x|y|i[aeiou])")
_VOWEL_START = re.compile(r"^[aeiouAEIOU]")


def determinate_article(noun: str, gender: str, plural: bool) -> str:
    special = bool(_SPECIAL_MASC_START.match(noun))
    vowel = bool(_VOWEL_START.match(noun))

    if gender == "m":
        if plural:
            return "gli" if (special or vowel) else "i"
        if vowel:
            return "l'"
        return "lo" if special else "il"
    else:  # femminile
        if plural:
            return "le"
        return "l'" if vowel else "la"


def indeterminate_article(noun: str, gender: str) -> str:
    special = bool(_SPECIAL_MASC_START.match(noun))
    vowel = bool(_VOWEL_START.match(noun))
    if gender == "m":
        return "uno" if special else "un"
    return "un'" if vowel else "una"


def explain_article_error(noun: str, gender: str, plural: bool, expected: str) -> str:
    gender_label = "männlich" if gender == "m" else "weiblich"
    reason = ""
    if _SPECIAL_MASC_START.match(noun) and gender == "m":
        reason = " ('lo/gli', da das Wort mit s+Konsonant/z/gn/ps/x/y beginnt)"
    elif _VOWEL_START.match(noun) and not plural:
        reason = " (Apostroph vor Vokal)"
    return f"Richtig wäre '{expected}' – '{noun}' ist {gender_label}{reason}."


def regular_plural(noun: str, gender: str) -> str:
    """Nur die produktive Grundregel. Für Ausnahmen (-co/-go, invariabel,
    fremdsprachige Wörter, ...) sollte lexeme.plural explizit gesetzt sein."""
    if noun.endswith("a") and gender == "f":
        return noun[:-1] + "e"
    if noun.endswith("o") and gender == "m":
        return noun[:-1] + "i"
    if noun.endswith("e"):
        return noun[:-1] + "i"
    # Invariabel (z.B. akzentuierte Endung, Konsonant, "crisi", ...)
    return noun


def explain_plural_error(noun: str, gender: str, expected: str) -> str:
    if noun.endswith("a") and gender == "f":
        rule = "Feminine Nomen auf -a bilden den Plural auf -e."
    elif noun.endswith("o") and gender == "m":
        rule = "Maskuline Nomen auf -o bilden den Plural auf -i."
    elif noun.endswith("e"):
        rule = "Nomen auf -e (m. und f.) bilden den Plural auf -i."
    else:
        rule = "Dieses Nomen ist unregelmäßig oder unveränderlich – am besten einzeln merken."
    return f"Richtig wäre '{expected}'. {rule}"
