from functools import cached_property


class __FSProxy:
    def __init__(self, path):
        self.__path = path

    @cached_property
    def datastore(self):
        from cs_demand_model.datastore import fs_datastore

        return fs_datastore(self.__path)

    def __getattr__(self, name):
        return getattr(self.datastore, name)


V1 = __FSProxy("sample://v1.zip")
