"""
Regelbasierte italienische Verbkonjugation.

PERSONS enthält lui/lei getrennt, damit passato-prossimo-Formen mit essere
(concordanza: andato/andata) korrekt geübt werden können. Für noi/voi/loro
wird vereinfachend die maskuline Form als Standard angenommen (üblich, wenn
das Geschlecht der Gruppe nicht bekannt ist) - das wird in der Erklärung
transparent gemacht.
"""
from typing import Optional

PERSONS = ["io", "tu", "lui", "lei", "noi", "voi", "loro"]

TENSES = [
    "presente", "imperfetto", "futuro_semplice", "passato_prossimo",
    "condizionale_semplice", "congiuntivo_presente",
]

TENSE_LABELS_DE = {
    "presente": "Präsens",
    "imperfetto": "Imperfekt",
    "futuro_semplice": "Futur I",
    "passato_prossimo": "Perfekt (passato prossimo)",
    "condizionale_semplice": "Konditional I",
    "congiuntivo_presente": "Konjunktiv Präsens",
}

_PRESENTE_ENDINGS = {
    "are": ["o", "i", "a", "a", "iamo", "ate", "ano"],
    "ere": ["o", "i", "e", "e", "iamo", "ete", "ono"],
    "ire": ["o", "i", "e", "e", "iamo", "ite", "ono"],
    "ire_isc": ["isco", "isci", "isce", "isce", "iamo", "ite", "iscono"],
}

_IMPERFETTO_ENDINGS = {
    "are": ["avo", "avi", "ava", "ava", "avamo", "avate", "avano"],
    "ere": ["evo", "evi", "eva", "eva", "evamo", "evate", "evano"],
    "ire": ["ivo", "ivi", "iva", "iva", "ivamo", "ivate", "ivano"],
    "ire_isc": ["ivo", "ivi", "iva", "iva", "ivamo", "ivate", "ivano"],
}

_FUTURO_ENDINGS = ["ò", "ai", "à", "à", "emo", "ete", "anno"]

_CONDIZIONALE_ENDINGS = ["ei", "esti", "ebbe", "ebbe", "emmo", "este", "ebbero"]

_CONGIUNTIVO_ENDINGS = {
    "are": ["i", "i", "i", "i", "iamo", "iate", "ino"],
    "ere": ["a", "a", "a", "a", "iamo", "iate", "ano"],
    "ire": ["a", "a", "a", "a", "iamo", "iate", "ano"],
    "ire_isc": ["isca", "isca", "isca", "isca", "iamo", "iate", "iscano"],
}

_PARTICIPIO_ENDING = {"are": "ato", "ere": "uto", "ire": "ito", "ire_isc": "ito"}

# Sehr gebräuchliche essere-Verben (Bewegung, Zustandsänderung, reflexiv u.ä.)
ESSERE_VERBS = {
    "andare", "venire", "arrivare", "partire", "entrare", "uscire", "salire",
    "scendere", "tornare", "restare", "rimanere", "diventare", "nascere",
    "morire", "essere", "stare", "cadere", "crescere", "riuscire", "piacere",
}


def conjugation_class(infinitive: str, explicit_class: Optional[str] = None) -> str:
    if explicit_class:
        return explicit_class
    if infinitive.endswith("are"):
        return "are"
    if infinitive.endswith("ere"):
        return "ere"
    if infinitive.endswith("ire"):
        return "ire"
    raise ValueError(f"Unbekannte Infinitiv-Endung: {infinitive}")


def _stem(infinitive: str) -> str:
    return infinitive[:-3]


def conjugate(
    infinitive: str,
    tense: str,
    person: str,
    conj_class: Optional[str] = None,
    irregular_forms: Optional[dict] = None,
    aux_override: Optional[str] = None,
    participle_override: Optional[str] = None,
) -> str:
    """Liefert die konjugierte Form. Prüft zuerst auf hinterlegte
    Ausnahmen (irregular_forms JSON), sonst wendet Regeln an."""

    if irregular_forms and tense in irregular_forms and person in irregular_forms[tense]:
        return irregular_forms[tense][person]

    cls = conjugation_class(infinitive, conj_class)
    stem = _stem(infinitive)
    idx = PERSONS.index(person)

    if tense == "presente":
        return stem + _PRESENTE_ENDINGS[cls][idx]

    if tense == "imperfetto":
        return stem + _IMPERFETTO_ENDINGS[cls][idx]

    if tense == "futuro_semplice":
        fut_stem = (stem + "er") if cls == "are" else infinitive[:-1]
        return fut_stem + _FUTURO_ENDINGS[idx]

    if tense == "condizionale_semplice":
        fut_stem = (stem + "er") if cls == "are" else infinitive[:-1]
        return fut_stem + _CONDIZIONALE_ENDINGS[idx]

    if tense == "congiuntivo_presente":
        return stem + _CONGIUNTIVO_ENDINGS[cls][idx]

    if tense == "passato_prossimo":
        aux = aux_override or ("essere" if infinitive in ESSERE_VERBS else "avere")
        participle = participle_override or (stem + _PARTICIPIO_ENDING[cls])

        aux_forms_avere = {"io": "ho", "tu": "hai", "lui": "ha", "lei": "ha", "noi": "abbiamo", "voi": "avete", "loro": "hanno"}
        aux_forms_essere = {"io": "sono", "tu": "sei", "lui": "è", "lei": "è", "noi": "siamo", "voi": "siete", "loro": "sono"}

        if aux == "essere":
            # Kongruenz Partizip mit Subjekt (vereinfachend: noi/voi/loro maskulin Plural)
            base = participle[:-1]  # ohne letztes 'o'
            agreement = {
                "io": "o", "tu": "o", "lui": "o", "lei": "a",
                "noi": "i", "voi": "i", "loro": "i",
            }[person]
            participle = base + agreement
            return f"{aux_forms_essere[person]} {participle}"
        return f"{aux_forms_avere[person]} {participle}"

    raise ValueError(f"Unbekannte Zeitform: {tense}")


def explain_conjugation_error(
    infinitive: str, tense: str, person: str, expected: str, given: str,
    conj_class: Optional[str] = None,
) -> str:
    cls = conjugation_class(infinitive, conj_class)
    label = TENSE_LABELS_DE.get(tense, tense)
    parts = [f"Richtig wäre '{expected}' ({label}, {person}, Verb auf -{cls.replace('_isc', '')})."]

    if tense == "presente" and cls != "irregular":
        parts.append(
            f"Verben auf -{cls.replace('ire_isc', 'ire (isc-Typ)')} bilden die {person}-Form mit der "
            f"Endung '-{_PRESENTE_ENDINGS[cls][PERSONS.index(person)]}'."
        )
    if tense == "passato_prossimo":
        aux = "essere" if infinitive in ESSERE_VERBS else "avere"
        parts.append(
            f"'{infinitive}' bildet das Perfekt mit '{aux}' + Partizip"
            + (", das Partizip passt sich bei essere-Verben in Endung an das Subjekt an (o/a/i)." if aux == "essere" else ".")
        )
    return " ".join(parts)
