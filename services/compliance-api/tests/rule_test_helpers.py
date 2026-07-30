from types import SimpleNamespace


def regulation_clause_lookup_for(
    section: str,
    threshold_value: float | None = 100.0,
    clause_id: int = 1,
):
    clause = SimpleNamespace(id=clause_id, threshold_value=threshold_value)

    def lookup(clause_section: str):
        if clause_section == section:
            return clause
        return None

    return lookup
