from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO
from zipfile import ZipFile

from ._api import DataFile, DataStore, Metadata


class ZipDataStore(DataStore):
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

    @property
    def files(self) -> DataFile:
        with ZipFile(self.path, "r") as zip:
            for info in zip.infolist():
                if not info.is_dir():
                    year, name = info.filename.split("/")
                    yield DataFile(
                        name=info.filename,
                        metadata=Metadata(
                            name=name, size=info.file_size, year=int(year)
                        ),
                    )

    @contextmanager
    def open(self, file) -> BinaryIO:
        filename = file.name if hasattr(file, "name") else file

        with ZipFile(self.path, "r") as zip:
            with zip.open(filename) as f:
                yield f
