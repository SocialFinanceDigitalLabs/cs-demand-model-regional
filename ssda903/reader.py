from django.core.files.storage import default_storage

from ssda903.datacontainer import DemandModellingDataContainer
from ssda903.datastore import LocalDataStore, StorageDataStore

_container_cache: dict = {}


def read_data(source) -> DemandModellingDataContainer:
    """
    Read data from source and return a pandas DataFrame
    """
    datastore = StorageDataStore(default_storage, source)
    cache_key = datastore.source_fingerprint
    if cache_key not in _container_cache:
        _container_cache.clear()
        _container_cache[cache_key] = DemandModellingDataContainer(datastore)

    return _container_cache[cache_key]


def read_local_data(files) -> DemandModellingDataContainer:
    """
    Read data from memory and return a pandas DataFrame
    """
    datastore = LocalDataStore(files)
    dc = DemandModellingDataContainer(datastore)
    return dc
