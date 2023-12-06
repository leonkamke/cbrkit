import csv
import tomllib
from collections import abc
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import orjson as json
import pandas as pd
import yaml
from pandas import DataFrame, Series

from cbrkit import model

__all__ = ("load_path", "load_dataframe")


class DataFrameCasebase(abc.Mapping[model.CaseName, model.CaseType]):
    df: DataFrame

    def __init__(self, df: DataFrame) -> None:
        self.df = df

    def __getitem__(self, key: int) -> Series:
        return self.df.iloc[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.df.index)

    def __len__(self) -> int:
        return len(self.df)


def load_dataframe(df: DataFrame) -> model.Casebase[pd.Series]:
    return DataFrameCasebase(df)


def _load_csv(path: model.FilePath) -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = {}

    with open(path) as fp:
        reader = csv.DictReader(fp)
        row: dict[str, str]

        for idx, row in enumerate(reader):
            data[str(idx)] = row

        return data


def _load_json(path: model.FilePath) -> dict[str, Any]:
    with open(path, "rb") as fp:
        return json.loads(fp.read())


def _load_toml(path: model.FilePath) -> dict[str, Any]:
    with open(path, "rb") as fp:
        return tomllib.load(fp)


def _load_yaml(path: model.FilePath) -> dict[str, Any]:
    data: dict[str, Any] = {}

    with open(path, "rb") as fp:
        for doc in yaml.safe_load_all(fp):
            data |= doc

    return data


def _load_txt(path: model.FilePath) -> str:
    with open(path) as fp:
        return fp.read()


SingleLoader = Callable[[model.FilePath], Any]
BatchLoader = Callable[[model.FilePath], dict[str, Any]]

# They contain the whole casebase in one file
_batch_loaders: dict[str, BatchLoader] = {
    ".json": _load_json,
    ".toml": _load_toml,
    ".yaml": _load_yaml,
    ".yml": _load_yaml,
    ".csv": _load_csv,
}

# They contain one case per file
# Since structured formats may also be used for single cases, they are also included here
_single_loaders: dict[str, SingleLoader] = {
    **_batch_loaders,
    ".txt": _load_txt,
}


def load_path(path: model.FilePath, pattern: str | None = None) -> model.Casebase[Any]:
    if isinstance(path, str):
        path = Path(path)

    cb: model.Casebase[Any] | None = None

    if path.is_file():
        cb = load_file(path)
    elif path.is_dir():
        cb = load_folder(path, pattern or "**/*")
    else:
        raise FileNotFoundError(path)

    if cb is None:
        raise NotImplementedError()

    return cb


def load_file(path: Path) -> model.Casebase[Any] | None:
    if path.suffix not in _batch_loaders:
        return None

    loader = _batch_loaders[path.suffix]
    cb = loader(path)

    return cb


def load_folder(path: Path, pattern: str) -> model.Casebase[Any] | None:
    cb: model.Casebase[Any] = {}

    for file in path.glob(pattern):
        if file.is_file() and file.suffix in _single_loaders:
            loader = _single_loaders[path.suffix]
            cb[file.name] = loader(file)

    if len(cb) == 0:
        return None

    return cb
