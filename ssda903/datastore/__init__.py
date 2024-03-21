import fs

from ._api import DataFile, DataStore, Metadata, TableType
from ._opener import fs_datastore
from ._sample import SampleFSOpener
from ._storage import StorageDataStore

fs.opener.registry.install(SampleFSOpener)


__all__ = [
    "StorageDataStore",
    "DataFile",
    "DataStore",
    "Metadata",
    "TableType",
    "fs_datastore",
]
