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
