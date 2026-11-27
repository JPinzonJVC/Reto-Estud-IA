"""Divisiones temporales para evitar entrenamiento con información futura."""

from dataclasses import dataclass

import pandas as pd

from app.modules.eda.ml.common.validation import (
    DatasetValidationError,
    validate_supervised_dataset,
)


@dataclass(frozen=True)
class TemporalDatasetSplit:
    """Particiones ordenadas para entrenamiento y validación temporal."""

    train: pd.DataFrame
    validation: pd.DataFrame
    cutoff: pd.Timestamp


def split_by_time(
    frame: pd.DataFrame,
    *,
    date_column: str,
    cutoff: str | pd.Timestamp,
    feature_columns: list[str],
    target_column: str,
    key_columns: list[str] | None = None,
    minimum_per_class: int = 2,
) -> TemporalDatasetSplit:
    """Separa train y validación usando un corte inclusivo solo en validación.

    Filas sin fecha o sin etiqueta se excluyen como no evaluables. El resto de filas
    deben superar las mismas validaciones antes de que el split pueda usarse.
    """
    if date_column not in frame.columns:
        raise DatasetValidationError(f"Falta la columna temporal `{date_column}`.")
    if target_column not in frame.columns:
        raise DatasetValidationError(f"Falta la etiqueta `{target_column}`.")
    cutoff_timestamp = pd.Timestamp(cutoff)
    dates = pd.to_datetime(frame[date_column], errors="coerce", utc=True)
    cutoff_utc = (
        cutoff_timestamp.tz_localize("UTC")
        if cutoff_timestamp.tzinfo is None
        else cutoff_timestamp.tz_convert("UTC")
    )
    eligible = frame.loc[dates.notna() & frame[target_column].notna()].copy()
    eligible[date_column] = dates.loc[eligible.index]
    train = eligible.loc[eligible[date_column] < cutoff_utc].copy()
    validation = eligible.loc[eligible[date_column] >= cutoff_utc].copy()

    keys = key_columns or []
    for partition_name, partition in (("train", train), ("validation", validation)):
        try:
            validate_supervised_dataset(
                partition,
                feature_columns=feature_columns,
                target_column=target_column,
                key_columns=keys,
                minimum_per_class=minimum_per_class,
            )
        except DatasetValidationError as error:
            raise DatasetValidationError(
                f"La partición temporal `{partition_name}` no es evaluable: {error}"
            ) from error

    return TemporalDatasetSplit(train=train, validation=validation, cutoff=cutoff_utc)
