MANIFEST_SCHEMA_VERSION = 1
VALID_BANDS = {"normal", "low", "severe"}


def _coerce_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_manifest_entry(meta, file_name="(entry)"):
    warnings = []

    bands = []
    for raw_band in _coerce_list(meta.get("band", [])):
        if not isinstance(raw_band, str):
            warnings.append(f"{file_name}: band 含非字串值，已忽略")
            continue
        normalized = raw_band.replace(".", ",")
        for token in normalized.split(","):
            band = token.strip()
            if not band:
                continue
            if band in VALID_BANDS:
                if band not in bands:
                    bands.append(band)
            else:
                warnings.append(f"{file_name}: 無效 band '{band}'，已忽略")

    contexts = []
    for raw_context in _coerce_list(meta.get("contexts", [])):
        if not isinstance(raw_context, str):
            warnings.append(f"{file_name}: contexts 含非字串值，已忽略")
            continue
        context = raw_context.strip()
        if not context:
            warnings.append(f"{file_name}: 空白 context，已忽略")
            continue
        if context not in contexts:
            contexts.append(context)

    try:
        weight = float(meta.get("weight", 1.0))
    except (TypeError, ValueError):
        weight = 1.0
        warnings.append(f"{file_name}: weight 無法轉成數字，已改回 1.0")

    return {
        "band": bands,
        "contexts": contexts,
        "weight": max(0.0, weight),
    }, warnings
