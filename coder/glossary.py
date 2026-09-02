GLOSSARY = {
    "homa": "fever",
    "kikohozi": "cough",
    "kuhara": "diarrhoea",
    "degedege": "convulsions",
    "bs": "blood smear",
    "co": "clinical officer",
    "anc": "antenatal clinic",
    "cva tenderness": "costovertebral angle tenderness",
    "sob": "shortness of breath",
}


def normalize_text(text: str) -> str:
    result = text.lower()
    for term, expansion in GLOSSARY.items():
        import re
        pattern = r'\b' + re.escape(term) + r'\b'
        result = re.sub(pattern, expansion, result, flags=re.IGNORECASE)
    return result


def normalize_episode_text(notes: list) -> list:
    return [{"t": n["t"], "author": n["author"], "text": normalize_text(n["text"])} for n in notes]