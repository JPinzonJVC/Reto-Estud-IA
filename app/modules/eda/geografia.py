"""Construcción y homologación de la jerarquía geográfica 3NF en la capa Silver."""

from typing import Any

import pandas as pd

from app.modules.eda.normalizer import limpiar_texto_y_mojibake

ALIAS_CIUDADES: dict[str, str] = {
    "bogota": "Bogotá",
    "bogotá": "Bogotá",
    "bogots": "Bogotá",
    "bogota d.c": "Bogotá",
    "bogota d.c.": "Bogotá",
    "bogotá d.c.": "Bogotá",
    "bogota dc": "Bogotá",
    "bogotá dc": "Bogotá",
    "bogota (bogota)": "Bogotá",
    "medellin": "Medellín",
    "medellín": "Medellín",
    "mede": "Medellín",
    "medelon": "Medellín",
    "itagui": "Itagüí",
    "itagüí": "Itagüí",
    "itaguí": "Itagüí",
    "monteria": "Montería",
    "montería": "Montería",
    "santa rosa de cabal": "Santa Rosa de Cabal",
    "cali": "Cali",
    "santiago de cali": "Cali",
    "barranquilla": "Barranquilla",
    "bucaramanga": "Bucaramanga",
    "cartagena": "Cartagena",
    "pereira": "Pereira",
    "manizales": "Manizales",
    "villavicencio": "Villavicencio",
    "popayan": "Popayán",
    "popayán": "Popayán",
    "ciudad de mexico": "Ciudad de México",
    "ciudad de méxico": "Ciudad de México",
    "caracas": "Caracas",
    "ciudad de guatemala": "Ciudad de Guatemala",
}

CIUDADES_INVALIDAS: frozenset[str] = frozenset(
    {"huy", "sin dato", "no aplica", "n/a", "na", "ninguna", "-", "."}
)

CATALOGO_BASE_CIUDAD_DEP_PAIS: dict[str, tuple[str, str]] = {
    "Bogotá": ("Bogotá D.C.", "Colombia"),
    "Medellín": ("Antioquia", "Colombia"),
    "Itagüí": ("Antioquia", "Colombia"),
    "Envigado": ("Antioquia", "Colombia"),
    "Bello": ("Antioquia", "Colombia"),
    "Rionegro": ("Antioquia", "Colombia"),
    "Sabaneta": ("Antioquia", "Colombia"),
    "La Estrella": ("Antioquia", "Colombia"),
    "Andes": ("Antioquia", "Colombia"),
    "Cali": ("Valle del Cauca", "Colombia"),
    "Yumbo": ("Valle del Cauca", "Colombia"),
    "Palmira": ("Valle del Cauca", "Colombia"),
    "Barranquilla": ("Atlántico", "Colombia"),
    "Bucaramanga": ("Santander", "Colombia"),
    "Floridablanca": ("Santander", "Colombia"),
    "Cartagena": ("Bolívar", "Colombia"),
    "Pereira": ("Risaralda", "Colombia"),
    "Santa Rosa de Cabal": ("Risaralda", "Colombia"),
    "Dosquebradas": ("Risaralda", "Colombia"),
    "Manizales": ("Caldas", "Colombia"),
    "Villavicencio": ("Meta", "Colombia"),
    "Popayán": ("Cauca", "Colombia"),
    "Montería": ("Córdoba", "Colombia"),
    "Ibagué": ("Tolima", "Colombia"),
    "Neiva": ("Huila", "Colombia"),
    "Pasto": ("Nariño", "Colombia"),
    "Cúcuta": ("Norte de Santander", "Colombia"),
    "Santa Marta": ("Magdalena", "Colombia"),
    "Armenia": ("Quindío", "Colombia"),
    "Tunja": ("Boyacá", "Colombia"),
    "Chía": ("Cundinamarca", "Colombia"),
    "Cajicá": ("Cundinamarca", "Colombia"),
    "Cota": ("Cundinamarca", "Colombia"),
    "Funza": ("Cundinamarca", "Colombia"),
    "Mosquera": ("Cundinamarca", "Colombia"),
    "Madrid": ("Cundinamarca", "Colombia"),
    "Sopó": ("Cundinamarca", "Colombia"),
    "Soacha": ("Cundinamarca", "Colombia"),
    "Tocancipá": ("Cundinamarca", "Colombia"),
    "Zipaquirá": ("Cundinamarca", "Colombia"),
    "Lenguazaque": ("Cundinamarca", "Colombia"),
    "Ciudad de México": ("Ciudad de México", "México"),
    "Caracas": ("Distrito Capital", "Venezuela"),
    "Ciudad de Guatemala": ("Guatemala", "Guatemala"),
}


def normalizar_nombre_ciudad(valor: Any) -> str | None:
    """Limpia y homologa variantes ortográficas de nombres de ciudad.

    Args:
        valor: Valor textual crudo de la ciudad.

    Returns:
        Nombre canónico de la ciudad o None si es inválido o vacío.

    """
    limpio = limpiar_texto_y_mojibake(valor)
    if limpio is None:
        return None
    clave = limpio.lower().strip()
    if clave in CIUDADES_INVALIDAS or len(clave) < 3:
        return None
    if clave in ALIAS_CIUDADES:
        return ALIAS_CIUDADES[clave]
    return limpio


class CatalogoGeografico:
    """Gestiona las tres dimensiones geográficas 3NF y resuelve claves foráneas.

    Attributes:
        dim_pais: DataFrame de silver_dim_pais.
        dim_departamento: DataFrame de silver_dim_departamento.
        dim_ciudad: DataFrame de silver_dim_ciudad.

    """

    def __init__(
        self,
        dim_pais: pd.DataFrame,
        dim_departamento: pd.DataFrame,
        dim_ciudad: pd.DataFrame,
        mapa_ciudad_default: dict[str, int],
        mapa_tripleta: dict[tuple[str, str, str], int],
    ) -> None:
        """Inicializa el catálogo con las tablas construidas e índices de búsqueda.

        Args:
            dim_pais: Tabla normalizada de países.
            dim_departamento: Tabla normalizada de departamentos.
            dim_ciudad: Tabla normalizada de ciudades.
            mapa_ciudad_default: Mapa de nombre_ciudad a id_ciudad canónico.
            mapa_tripleta: Mapa exacto de (pais, departamento, ciudad) a id_ciudad.

        """
        self.dim_pais = dim_pais
        self.dim_departamento = dim_departamento
        self.dim_ciudad = dim_ciudad
        self._mapa_ciudad_default = mapa_ciudad_default
        self._mapa_tripleta = mapa_tripleta

    def resolver_id_ciudad(
        self,
        ciudad: Any,
        departamento: Any = None,
        pais: Any = None,
    ) -> int | None:
        """Resuelve el id_ciudad entero para una ubicación o retorna None.

        Args:
            ciudad: Nombre de la ciudad.
            departamento: Nombre opcional del departamento o región.
            pais: Nombre opcional del país.

        Returns:
            Clave primaria id_ciudad o None si no existe asociación confiable.

        """
        ciu_norm = normalizar_nombre_ciudad(ciudad)
        if ciu_norm is None:
            return None
        if ciu_norm in CATALOGO_BASE_CIUDAD_DEP_PAIS:
            dep_fijo, pais_fijo = CATALOGO_BASE_CIUDAD_DEP_PAIS[ciu_norm]
            return self._mapa_tripleta.get((pais_fijo, dep_fijo, ciu_norm))

        dep_norm = limpiar_texto_y_mojibake(departamento)
        pais_norm = limpiar_texto_y_mojibake(pais) or "Colombia"
        if dep_norm is not None:
            tripleta = (pais_norm, dep_norm, ciu_norm)
            if tripleta in self._mapa_tripleta:
                return self._mapa_tripleta[tripleta]
        return self._mapa_ciudad_default.get(ciu_norm)


def _recolectar_tripletas_origen(
    bronze: dict[str, pd.DataFrame],
) -> list[tuple[str, str, str]]:
    """Extrae todas las combinaciones válidas (pais, departamento, ciudad) de Bronze.

    Args:
        bronze: Diccionario de DataFrames de la capa Bronze.

    Returns:
        Lista ordenada y deduplicada de tripletas geográficas válidas.

    """
    tripletas: set[tuple[str, str, str]] = set()
    mapa_emp_ciu: dict[str, tuple[str, str]] = dict(CATALOGO_BASE_CIUDAD_DEP_PAIS)

    df_emp = bronze["dim_empresas"]
    for _, row in df_emp.iterrows():
        ciu = normalizar_nombre_ciudad(row.get("ciudad"))
        if ciu is None:
            continue
        if ciu in CATALOGO_BASE_CIUDAD_DEP_PAIS:
            dep, pais = CATALOGO_BASE_CIUDAD_DEP_PAIS[ciu]
        else:
            dep = limpiar_texto_y_mojibake(row.get("region_departamento")) or "Sin dato"
            pais = limpiar_texto_y_mojibake(row.get("pais")) or "Colombia"
            mapa_emp_ciu.setdefault(ciu, (dep, pais))
        tripletas.add((pais, dep, ciu))

    series_ciudades = [
        bronze["dim_personas"].get("ciudad"),
        bronze["fact_asistencias"].get("ciudad_evento"),
        bronze["fact_encuestas_satisfaccion"].get("ciudad"),
    ]
    for serie in series_ciudades:
        if serie is None:
            continue
        for val in serie.dropna():
            ciu = normalizar_nombre_ciudad(val)
            if ciu is None:
                continue
            dep, pais = mapa_emp_ciu.get(ciu, ("Sin especificar", "Colombia"))
            tripletas.add((pais, dep, ciu))

    for ciu_fija in ("Bogotá", "Medellín"):
        dep_f, pais_f = CATALOGO_BASE_CIUDAD_DEP_PAIS[ciu_fija]
        tripletas.add((pais_f, dep_f, ciu_fija))

    return sorted(tripletas)


def construir_catalogo_geografico(
    bronze: dict[str, pd.DataFrame],
) -> CatalogoGeografico:
    """Construye silver_dim_pais, silver_dim_departamento y silver_dim_ciudad.

    Args:
        bronze: Diccionario de DataFrames de la capa Bronze.

    Returns:
        Instancia de CatalogoGeografico con las 3 tablas normalizadas y buscador FK.

    """
    tripletas = _recolectar_tripletas_origen(bronze)

    paises_unicos = sorted({p for p, _, _ in tripletas})
    mapa_pais: dict[str, int] = {p: idx + 1 for idx, p in enumerate(paises_unicos)}
    dim_pais = pd.DataFrame(
        [{"id_pais": pid, "nombre_pais": p} for p, pid in mapa_pais.items()]
    )

    deps_unicos = sorted({(mapa_pais[p], d) for p, d, _ in tripletas})
    mapa_dep: dict[tuple[int, str], int] = {
        par: idx + 1 for idx, par in enumerate(deps_unicos)
    }
    dim_departamento = pd.DataFrame(
        [
            {
                "id_departamento": did,
                "id_pais": pid,
                "nombre_departamento": dep_nom,
            }
            for (pid, dep_nom), did in mapa_dep.items()
        ]
    )

    ciudades_unicas = sorted(
        {(mapa_dep[(mapa_pais[p], d)], c, p, d) for p, d, c in tripletas},
        key=lambda item: (item[0], item[1]),
    )
    filas_ciu: list[dict[str, Any]] = []
    mapa_tripleta: dict[tuple[str, str, str], int] = {}
    mapa_ciudad_default: dict[str, int] = {}

    for idx, (did, ciu_nom, p_nom, d_nom) in enumerate(ciudades_unicas, start=1):
        filas_ciu.append(
            {
                "id_ciudad": idx,
                "id_departamento": did,
                "nombre_ciudad": ciu_nom,
            }
        )
        mapa_tripleta[(p_nom, d_nom, ciu_nom)] = idx
        mapa_ciudad_default.setdefault(ciu_nom, idx)

    dim_ciudad = pd.DataFrame(filas_ciu)
    return CatalogoGeografico(
        dim_pais=dim_pais,
        dim_departamento=dim_departamento,
        dim_ciudad=dim_ciudad,
        mapa_ciudad_default=mapa_ciudad_default,
        mapa_tripleta=mapa_tripleta,
    )


def extraer_ciudad_sede_evento(
    nombre_evento: Any,
    modalidad: Any,
    geo: CatalogoGeografico,
) -> int | None:
    """Determina id_ciudad_evento solo cuando el evento presencial explicita su sede.

    Args:
        nombre_evento: Título oficial del evento.
        modalidad: Modalidad del evento ('Presencial', 'Virtual', 'Híbrido').
        geo: Catálogo geográfico activo.

    Returns:
        Identificador de ciudad sede o None si es virtual o no está especificada.

    """
    mod_txt = limpiar_texto_y_mojibake(modalidad) or ""
    if mod_txt.lower() == "virtual":
        return None
    titulo = (limpiar_texto_y_mojibake(nombre_evento) or "").lower()
    for etiqueta, ciudad_can in (
        ("(bogotá)", "Bogotá"),
        ("(bogota)", "Bogotá"),
        ("(medellín)", "Medellín"),
        ("(medellin)", "Medellín"),
        ("(cali)", "Cali"),
        ("(barranquilla)", "Barranquilla"),
    ):
        if etiqueta in titulo:
            return geo.resolver_id_ciudad(ciudad_can)
    return None
