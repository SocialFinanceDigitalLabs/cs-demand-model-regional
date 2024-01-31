import io
from abc import ABC
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, Iterator

import pandas as pd


class TableType(Enum):
    pass


@dataclass
class Metadata:
    name: str
    size: int
    year: int = None
    table: TableType = None


@dataclass
class DataFile:
    name: str
    metadata: Metadata


class DataStore(ABC):
    @property
    def files(self) -> Iterator[DataFile]:
        """
        Return information about all the files in this datastore
        """
        raise NotImplementedError

    @contextmanager
    def open(self, file: [str | DataFile]) -> BinaryIO:
        """
        Open a file either by name or represented by a DataFile object

        :param file: The name of the file or a DataFile object
        """
        raise NotImplementedError

    def to_dataframe(self, file: [str | DataFile]) -> pd.DataFrame:
        formats = [pd.read_csv, pd.read_excel, pd.read_json]
        with self.open(file) as f:
            if not f.seekable():
                f = io.BytesIO(f.read())
            length = f.seek(0, 2)  # Seek to end of file
            if length < 2:
                raise ValueError("File is empty")

            f.seek(0, 0)
            for fmt in formats:
                try:
                    return fmt(f)
                except:
                    pass
        raise ValueError("Could not find a format able to read this file")
