import pandas as pd

from ssda903.config import Config
from ssda903.datacontainer import DemandModellingDataContainer
from ssda903.datastore import fs_datastore


def read_data(source) -> DemandModellingDataContainer:
    """
    Read data from source and return a pandas DataFrame
    """
    datastore = fs_datastore(source)
    config = Config()
    dc = DemandModellingDataContainer(datastore, config)
    return dc
