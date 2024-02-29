from typing import Any, Mapping


class ConfigurationSource:
    """
    This class allows access to the key properties of a dictionary of configuration values.

    It is here to allow us to change configuration and maintain backwards compatibility.

    It is used by the factory methods to actually create the program values.
    """

    def __init__(self, config: Mapping[str, Any]):
        self._config = config
        self._config_config = config["config"]

    @property
    def name(self):
        return self._config["name"]

    @property
    def description(self):
        return self._config["description"]

    @property
    def version(self):
        return self._config["version"]

    @property
    def age_brackets(self):
        return self._config_config["AgeBrackets"]

    @property
    def placement_categories(self):
        return self._config_config["PlacementCategories"]

    @property
    def costs(self):
        return self._config_config["costs"]

    @property
    def year_in_days(self):
        return self._config_config["YearInDays"]

    @property
    def src(self):
        return self._config
