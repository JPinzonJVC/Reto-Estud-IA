"""Rutinas de normalización y estandarización de datos en la capa Silver."""

import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

REEMPLAZOS_MOJIBAKE: tuple[tuple[str, str], ...] = (
    ("Ã¡", "á"),
    ("Ã©", "é"),
    ("Ã­", "í"),
    ("Ã³", "ó"),
    ("Ãº", "ú"),
    ("Ã±", "ñ"),
    ("Ã\x81", "Á"),
    ("Ã\x89", "É"),
    ("Ã\x8d", "Í"),
    ("Ã\x93", "Ó"),
    ("Ã\x9a", "Ú"),
    ("Ã\x91", "Ñ"),
    ("ﾃｼ", "ü"),
    ("ﾃ｡", "á"),
    ("ﾃｩ", "é"),
    ("ﾃｭ", "í"),
    ("ﾃｳ", "ó"),
    ("ﾃｺ", "ú"),
    ("ﾃｱ", "ñ"),
    ("\xa0", " "),
)

CIUDADES_CANONICAS: dict[str, str] = {
    "bogota": "Bogotá",
    "bogota dc": "Bogotá",
    "bogota d c": "Bogotá",
    "bogota bogota": "Bogotá",
    "bigota": "Bogotá",
    "bogots": "Bogotá",
    "medellin": "Medellín",
    "medellib": "Medellín",
    "medelon": "Medellín",
    "mediellin": "Medellín",
    "mede": "Medellín",
    "itagui": "Itagüí",
    "barranquilla": "Barranquilla",
    "barranquila": "Barranquilla",
    "barra": "Barranquilla",
    "cajica": "Cajicá",
    "chia": "Chía",
    "sopo": "Sopó",
    "gachancipa": "Gachancipá",
    "monteria": "Montería",
    "jamundi": "Jamundí",
    "guacari": "Guacarí",
    "riofrio": "Riofrío",
    "tulua": "Tuluá",
    "ibague": "Ibagué",
    "popayan": "Popayán",
    "facatativa": "Facatativá",
    "fusagasuga": "Fusagasugá",
    "apartado": "Apartadó",
    "cali": "Cali",
    "cartagena": "Cartagena",
    "bucaramanga": "Bucaramanga",
    "envigado": "Envigado",
    "funza": "Funza",
    "cota": "Cota",
    "neiva": "Neiva",
    "pereira": "Pereira",
    "santa marta": "Santa Marta",
    "la estrella": "La Estrella",
    "floridablanca giron": "Floridablanca",
    "amdes": "Andes",
    "madrid espana": "Madrid (España)",
}

DEPARTAMENTOS_COLOMBIA: dict[str, str] = {
    "antioquia": "Antioquia",
    "quindio": "Quindío",
    "cundinamarca": "Cundinamarca",
    "valle del cauca": "Valle del Cauca",
    "atlantico": "Atlántico",
    "bolivar": "Bolívar",
    "santander": "Santander",
    "norte de santander": "Norte de Santander",
    "boyaca": "Boyacá",
    "tolima": "Tolima",
    "huila": "Huila",
    "risaralda": "Risaralda",
    "caldas": "Caldas",
    "meta": "Meta",
    "cesar": "Cesar",
    "cordoba": "Córdoba",
    "magdalena": "Magdalena",
    "narino": "Nariño",
    "cauca": "Cauca",
    "sucre": "Sucre",
    "casanare": "Casanare",
    "caqueta": "Caquetá",
    "choco": "Chocó",
    "la guajira": "La Guajira",
    "arauca": "Arauca",
    "putumayo": "Putumayo",
    "amazonas": "Amazonas",
    "guaviare": "Guaviare",
    "guainia": "Guainía",
    "vaupes": "Vaupés",
    "vichada": "Vichada",
    "san andres": "San Andrés",
}

PAISES_NO_CIUDAD: frozenset[str] = frozenset(
    {
        "colombia",
        "mexico",
        "espana",
        "peru",
        "chile",
        "argentina",
        "ecuador",
        "panama",
        "venezuela",
        "guatemala",
        "estados unidos",
        "usa",
    }
)

CIUDADES_INVALIDAS: frozenset[str] = frozenset({"ciudad", "huy", "sin dato", "na", "n a"})

SECTORES_CANONICOS: dict[str, str] = {
    "asociacones gremiales": "Asociaciones Gremiales",
    "asociaciones gremiales": "Asociaciones Gremiales",
    "tecnologia": "Tecnología",
    "entidades sin animo de lucro": "Entidades Sin Ánimo de Lucro",
    "farmaceutico y quimicos": "Farmacéutico y Químicos",
    "cajas de compensacion": "Cajas de Compensación",
    "consultoria especializada en rrhh": "Consultoría Especializada en RRHH",
    "medios y comunicaciones": "Medios y Comunicaciones",
}

PREPOSICIONES_ES: frozenset[str] = frozenset({"de", "del", "la", "las", "los", "y"})

VALORES_VERDADEROS: frozenset[str] = frozenset(
    {
        "1",
        "1.0",
        "true",
        "si",
        "sí",
        "yes",
        "con costo",
        "sí, autorizo el tratamiento de mis datos personales",
        "si, autorizo el tratamiento de mis datos personales",
        "autorizo",
    }
)

VALORES_FALSOS: frozenset[str] = frozenset(
    {
        "0",
        "0.0",
        "false",
        "no",
        "sin costo",
        "no autorizo",
    }
)

MESES_ES_A_EN: dict[str, str] = {
    "ene": "Jan",
    "feb": "Feb",
    "mar": "Mar",
    "abr": "Apr",
    "may": "May",
    "jun": "Jun",
    "jul": "Jul",
    "ago": "Aug",
    "sep": "Sep",
    "oct": "Oct",
    "nov": "Nov",
    "dic": "Dec",
}


def limpiar_texto_y_mojibake(valor: Any) -> str | None:
    """Limpia espacios, mojibake común y representaciones vacías en textos.

    Args:
        valor: Valor de entrada a normalizar.

    Returns:
        Cadena limpia o None si el valor es nulo o vacío.

    """
    if pd.isna(valor):
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() in ("nan", "none", "null", "nat"):
        return None
    for mal, bien in REEMPLAZOS_MOJIBAKE:
        texto = texto.replace(mal, bien)
    return re.sub(r"\s+", " ", texto).strip()


def normalizar_encabezado_snake_case(nombre: str) -> str:
    """Convierte encabezados heterogéneos de CSV crudos a formato snake_case.

    Args:
        nombre: Nombre original de la columna en el archivo CSV.

    Returns:
        Identificador de columna normalizado en snake_case.

    """
    limpio = re.sub(r"\[(?:anonimizado|eliminado)\]", "", str(nombre), flags=re.I)
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", limpio) if not unicodedata.combining(c)
    )
    snake = re.sub(r"[^a-zA-Z0-9]+", "_", sin_tildes.strip().lower()).strip("_")
    return snake or "columna_sin_nombre"


def normalizar_booleano(valor: Any) -> bool | None:
    """Convierte representaciones textuales o numéricas a booleano estándar.

    Args:
        valor: Valor de entrada (ej. 'Con costo', 'Sin costo', 'Si', 'No', 1, 0).

    Returns:
        Booleano Python o None si el valor no es interpretable o es nulo.

    """
    if isinstance(valor, bool):
        return valor
    texto = limpiar_texto_y_mojibake(valor)
    if texto is None:
        return None
    clave = texto.lower()
    if clave in VALORES_VERDADEROS:
        return True
    if clave in VALORES_FALSOS:
        return False
    return None


def normalizar_fecha_iso(valor: Any) -> str | None:
    """Normaliza fechas heterogéneas (incluyendo meses en español) a YYYY-MM-DD.

    Args:
        valor: Valor de fecha o timestamp en cualquier formato soportado.

    Returns:
        Fecha en formato ISO YYYY-MM-DD o None si no es parseable.

    """
    texto = limpiar_texto_y_mojibake(valor)
    if texto is None:
        return None
    texto_norm = texto.replace("a. m.", "AM").replace("p. m.", "PM")
    for mes_es, mes_en in MESES_ES_A_EN.items():
        texto_norm = re.sub(
            rf"\b{mes_es}\.?",
            mes_en,
            texto_norm,
            flags=re.IGNORECASE,
        )
    ts = pd.to_datetime(texto_norm, errors="coerce")
    if pd.isna(ts):
        return None
    return str(ts.strftime("%Y-%m-%d"))


def _clave_canonica(texto: str) -> str:
    """Genera una clave ASCII en minúsculas sin tildes ni puntuación."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]+", " ", sin_tildes.lower()).strip()


def _title_case_es(texto: str) -> str:
    """Aplica capitalización legible preservando preposiciones en español."""
    palabras = texto.split()
    resultado: list[str] = []
    for idx, palabra in enumerate(palabras):
        low = palabra.lower()
        if idx > 0 and low in PREPOSICIONES_ES:
            resultado.append(low)
        else:
            resultado.append(palabra[:1].upper() + palabra[1:].lower())
    return " ".join(resultado)


def extraer_departamento_si_aplica(valor: Any) -> str | None:
    """Retorna el nombre canónico del departamento si el texto corresponde a uno.

    Args:
        valor: Valor textual reportado en un campo geográfico.

    Returns:
        Nombre canónico del departamento colombiano o None si no es departamento.

    """
    texto = limpiar_texto_y_mojibake(valor)
    if texto is None:
        return None
    clave = _clave_canonica(texto)
    return DEPARTAMENTOS_COLOMBIA.get(clave)


def normalizar_ciudad(valor: Any) -> str | None:
    """Homologa variantes ortográficas, mayúsculas y tildes de nombres de ciudades.

    Excluye departamentos colombianos, nombres de países y placeholders inválidos
    para que la columna ciudad contenga exclusivamente municipios/ciudades.

    Args:
        valor: Nombre de ciudad proveniente de CRM, asistencias o encuestas.

    Returns:
        Nombre canónico de la ciudad o None si es nulo, departamento, país o inválido.

    """
    texto = limpiar_texto_y_mojibake(valor)
    if texto is None:
        return None
    clave = _clave_canonica(texto)
    if (
        not clave
        or clave in CIUDADES_INVALIDAS
        or clave in DEPARTAMENTOS_COLOMBIA
        or clave in PAISES_NO_CIUDAD
    ):
        return None
    if clave in CIUDADES_CANONICAS:
        return CIUDADES_CANONICAS[clave]
    if texto.isupper() or texto.islower():
        return _title_case_es(texto)
    return texto


def normalizar_sector(valor: Any) -> str | None:
    """Homologa variantes ortográficas y de tildes en sectores económicos.

    Args:
        valor: Nombre de sector económico proveniente del CRM.

    Returns:
        Nombre canónico del sector económico o None si es nulo.

    """
    texto = limpiar_texto_y_mojibake(valor)
    if texto is None:
        return None
    clave = _clave_canonica(texto)
    if clave in SECTORES_CANONICOS:
        return SECTORES_CANONICOS[clave]
    return texto


def normalizar_dataframe_silver(
    df: pd.DataFrame,
    cols_texto: tuple[str, ...] = (),
    cols_bool: tuple[str, ...] = (),
    cols_fecha: tuple[str, ...] = (),
    cols_ciudad: tuple[str, ...] = (),
    cols_sector: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Aplica reglas de normalización Silver sobre columnas de texto, bool, fecha y catálogos.

    Args:
        df: DataFrame de entrada proveniente de Bronze.
        cols_texto: Columnas de texto a limpiar de mojibake y espacios.
        cols_bool: Columnas booleanas a estandarizar.
        cols_fecha: Columnas de fecha a estandarizar en formato ISO YYYY-MM-DD.
        cols_ciudad: Columnas geográficas de ciudad a homologar.
        cols_sector: Columnas de sector económico a homologar.

    Returns:
        Copia del DataFrame con las columnas normalizadas.

    """
    resultado = df.copy()
    for col in cols_texto:
        if col in resultado.columns:
            resultado[col] = resultado[col].apply(limpiar_texto_y_mojibake)
    for col in cols_ciudad:
        if col in resultado.columns:
            resultado[col] = resultado[col].apply(normalizar_ciudad)
    for col in cols_sector:
        if col in resultado.columns:
            resultado[col] = resultado[col].apply(normalizar_sector)
    for col in cols_bool:
        if col in resultado.columns:
            resultado[col] = resultado[col].apply(normalizar_booleano)
    for col in cols_fecha:
        if col in resultado.columns:
            resultado[col] = resultado[col].apply(normalizar_fecha_iso)
    return resultado


def leer_y_normalizar_evento_raw(ruta_csv: Path) -> pd.DataFrame:
    """Lee y normaliza un reporte crudo individual de asistencia en Bronze.

    Args:
        ruta_csv: Ruta al archivo CSV crudo dentro de bronze/raw_csv/Asistencia eventos.

    Returns:
        DataFrame limpio sin filas de título, sin columnas [eliminado] y en snake_case.

    """
    df_raw = pd.read_csv(ruta_csv, header=None, dtype=str)
    header_idx = 0
    for pos, (_, row) in enumerate(df_raw.head(5).iterrows()):
        fila_txt = " ".join(str(v) for v in row.dropna().tolist()).lower()
        if "id_empresa" in fila_txt or "id_persona" in fila_txt:
            header_idx = pos
            break

    encabezados = [str(v) for v in df_raw.iloc[header_idx].tolist()]
    inicio_datos = header_idx + 1
    df_datos = df_raw.iloc[inicio_datos:].copy()
    df_datos.columns = encabezados
    cols_validas = [
        c
        for c in df_datos.columns
        if c and c.lower() != "nan" and "[eliminado]" not in c.lower()
    ]
    df_datos = df_datos[cols_validas].dropna(how="all").reset_index(drop=True)
    df_datos.columns = [normalizar_encabezado_snake_case(c) for c in df_datos.columns]
    if "costo" in df_datos.columns:
        df_datos["tiene_costo"] = df_datos["costo"].apply(normalizar_booleano)
    return df_datos
