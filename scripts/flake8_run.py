"""Script para ejecutar flake8 en archivos .py siguiendo los estándares del equipo."""

import subprocess
import sys
from pathlib import Path

# Errores deshabilitados:
# W503: line break before binary operator
# W504: line break after binary operator
FLAKE8_IGNORE = "W503,W504"
MAX_LINE_LENGTH = "90"


def find_py_files(root: Path) -> list[Path]:
    """Busca archivos .py en el directorio raíz.

    Busca recursivamente todos los archivos con extensión .py, excluyendo
    directorios de entornos virtuales y archivos __init__.py.

    Args:
        root: Ruta del directorio raíz donde buscar.

    Returns:
        Lista de rutas a los archivos .py encontrados.

    """
    excluded_files = {"__init__.py"}
    excluded_dirs = {"venv", ".venv", ".git", "__pycache__", "build", "dist"}

    pyfiles: list[Path] = []
    for p in root.rglob("*.py"):
        if p.name in excluded_files:
            continue

        is_excluded_dir = False
        for part in p.parts:
            if part in excluded_dirs:
                is_excluded_dir = True
                break

        if not is_excluded_dir:
            pyfiles.append(p)

    return pyfiles


def run_flake8(files: list[Path]) -> int:
    """Ejecuta flake8 sobre una lista de archivos.

    Args:
        files: Lista de rutas de archivos a analizar.

    Returns:
        Código de salida de flake8.

    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "flake8",
            f"--extend-ignore={FLAKE8_IGNORE}",
            f"--max-line-length={MAX_LINE_LENGTH}",
            "--statistics",
            "--count",
            *map(str, files),
        ],
        check=False,
    )
    return result.returncode


def main() -> None:
    """Función principal del script.

    Coordina la búsqueda de archivos y la ejecución de flake8.

    """
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    files = find_py_files(root)

    if not files:
        print("No se encontraron archivos .py para analizar.", file=sys.stderr)
        sys.exit(0)

    sys.exit(run_flake8(files))


if __name__ == "__main__":
    main()
