from django.core.files.storage import default_storage

from ssda903.datacontainer import DemandModellingDataContainer
from ssda903.datastore import LocalDataStore, StorageDataStore


def read_data(source) -> DemandModellingDataContainer:
    """
    Read data from source and return a pandas DataFrame
    """
    datastore = StorageDataStore(default_storage, source)
    dc = DemandModellingDataContainer(datastore)
    return dc


def read_local_data(files) -> DemandModellingDataContainer:
    """
    Read data from memory and return a pandas DataFrame
    """
    datastore = LocalDataStore(files)
    dc = DemandModellingDataContainer(datastore)
    return dc
