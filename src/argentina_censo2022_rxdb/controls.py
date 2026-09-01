# Development-source controls reproduced against the April 2025 VP corpus.
# They are intentionally adapter data, not generic extractor constants.
APRIL_2025_VP_COUNTS = {
    "VIVIENDA": 17_783_029,
    "HOGAR": 15_932_302,
    "PERSONA": 45_618_787,
}

KNOWN_VARIABLE_ANOMALIES = {
    "PERSONA.HNVUA": "name/alias ambiguity under tested RedEngine 1.1 and 1.3 runtimes",
}

# Permanent small-area laboratories established during extraction research.
PERMANENT_LABORATORIES = {
    "tiny_radio": {
        "selection_entity": "RADIO",
        "selection_code": "061120902",
        "counts": {"VIVIENDA": 1, "HOGAR": 1, "PERSONA": 1},
    },
    "relational_radio": {
        "selection_entity": "RADIO",
        "selection_code": "061471101",
        "counts": {"VIVIENDA": 73, "HOGAR": 56, "PERSONA": 137},
    },
    "large_radio": {
        "selection_entity": "RADIO",
        "selection_code": "064279901",
        "counts": {"PERSONA": 6_992},
    },
    "frac": {
        "selection_entity": "FRAC",
        "selection_code": "0614711",
        "counts": {"VIVIENDA": 130, "HOGAR": 72, "PERSONA": 173},
    },
}
