import fs

from ._api import DataFile, DataStore, Metadata, TableType
from ._opener import fs_datastore
from ._sample import SampleFSOpener

fs.opener.registry.install(SampleFSOpener)


__all__ = ["DataFile", "DataStore", "Metadata", "TableType", "fs_datastore"]
