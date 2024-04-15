import logging
import os
from contextlib import contextmanager
from typing import BinaryIO

from django.core.files.storage import Storage

from ._api import DataFile, DataStore, Metadata

logger = logging.getLogger(__name__)


class StorageDataStore(DataStore):
    """DataStore implementation for Django storage backends."""

    def __init__(self, storage: Storage, path: str):
        self.__storage = storage
        self.__path = path

    @property
    def files(self) -> DataFile:
        filenames = self.__storage.listdir(self.__path)[1]
        for name in filenames:
            filepath = os.path.join(self.__path, name)
            yield DataFile(
                name=name,
                metadata=Metadata(
                    name=name, size=self.__storage.size(filepath), path=filepath
                ),
            )

    @contextmanager
    def open(self, file: DataFile) -> BinaryIO:
        with self.__storage.open(file.metadata.path, "rb") as f:
            yield f
