"""Calcula y persiste resultados descriptivos ML en PostgreSQL Gold."""

import json

from app.database import get_session_factory
from app.modules.eda.ml.persistence import generate_descriptive_results


def main() -> None:
    """Genera un corte idempotente e informa conteos por caso de uso."""
    session_factory = get_session_factory()
    with session_factory() as db:
        counts = generate_descriptive_results(db)
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
