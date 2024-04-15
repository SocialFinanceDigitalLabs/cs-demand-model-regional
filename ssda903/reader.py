from django.core.files.storage import default_storage

from ssda903.config import Config
from ssda903.datacontainer import DemandModellingDataContainer
from ssda903.datastore import StorageDataStore


def read_data(source) -> DemandModellingDataContainer:
    """
    Read data from source and return a pandas DataFrame
    """
    datastore = StorageDataStore(default_storage, source)
    config = Config()
    dc = DemandModellingDataContainer(datastore, config)
    return dc
