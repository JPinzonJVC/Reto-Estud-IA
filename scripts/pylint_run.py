"""Script que ejecuta pylint siguiendo los estándares de calidad para Python."""

import shutil
import subprocess
import sys
from pathlib import Path

# Errores deshabilitados según estándar de QX IDI:
# E0401: import-error
# E0611: no-name-in-module
# R0903: too-few-public-methods
# R0913: too-many-arguments
# R0801: duplicate-code
# W: warning
PYLINT_DISABLE = "E0401,E0611,R0903,R0913,R0801,W"


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


def run_pylint(files: list[Path]) -> tuple[str, int]:
    """Ejecuta pylint sobre una lista de archivos.

    Ejecuta el módulo pylint usando el intérprete de Python actual con
    las configuraciones de deshabilitación definidas.

    Args:
        files: Lista de rutas de archivos a analizar.

    Returns:
        Una tupla con la salida estándar y el código de salida de pylint.

    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pylint",
            f"--disable={PYLINT_DISABLE}",
            "--max-locals=20",
            "--output-format=text",
            *map(str, files),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout, result.returncode


def evaluate_exit_code(exit_code: int) -> int:
    """Evalúa el código de salida usando pylint-exit o análisis de bits.

    Args:
        exit_code: Código de retorno original emitido por pylint.

    Returns:
        Código de retorno final tras filtrar advertencias aceptables.

    """
    pylint_exit_bin = shutil.which("pylint-exit")
    if pylint_exit_bin:
        res = subprocess.run(
            [
                pylint_exit_bin,
                "--error-fail",
                "--refactor-fail",
                "--convention-fail",
                str(exit_code),
            ],
            check=False,
        )
        return res.returncode

    # Fallback si la herramienta no está disponible en el entorno
    # Máscara de códigos: fatal(1), error(2), refactor(8), convention(16), usage(32)
    critical_errors_mask = 1 | 2 | 8 | 16 | 32
    if exit_code & critical_errors_mask:
        return exit_code
    return 0


def main() -> None:
    """Función principal del script.

    Coordina la búsqueda de archivos, la ejecución de pylint y el manejo
    de códigos de salida mediante pylint-exit.

    """
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    files = find_py_files(root)

    if not files:
        print("No se encontraron archivos .py para analizar.", file=sys.stderr)
        sys.exit(0)

    output, exit_code = run_pylint(files)
    print(output)

    final_code = evaluate_exit_code(exit_code)
    if final_code != 0:
        sys.exit(final_code)


if __name__ == "__main__":
    main()
