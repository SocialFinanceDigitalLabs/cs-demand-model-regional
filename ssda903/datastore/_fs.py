import logging
from contextlib import contextmanager
from typing import BinaryIO

from fs.base import FS

from ._api import DataFile, DataStore, Metadata

logger = logging.getLogger(__name__)


class FSDataStore(DataStore):
    def __init__(self, filesystem: FS):
        self.__filesystem = filesystem

    @property
    def files(self) -> DataFile:
        for info in self.__filesystem.walk.files(filter=["*.csv"]):
            if info[0] == "/":
                info = info[1:]

            if "/" in info:
                year, name = info.split("/")
                yield DataFile(
                    name=info,
                    metadata=Metadata(
                        name=name, size=self.__filesystem.getsize(info), year=int(year)
                    ),
                )
            else:
                yield DataFile(
                    name=info,
                    metadata=Metadata(name=info, size=self.__filesystem.getsize(info)),
                )

    @contextmanager
    def open(self, file) -> BinaryIO:
        filename = file.name if hasattr(file, "name") else file

        with self.__filesystem.open(filename, "rb") as f:
            yield f
