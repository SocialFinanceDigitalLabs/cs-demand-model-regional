from pathlib import Path

from fs.opener import Opener
from fs.osfs import OSFS


class SampleFSOpener(Opener):
    protocols = ["sample"]

    def open_fs(self, fs_url, parse_result, writeable, create, cwd):
        import cs_demand_model_samples

        path = Path(cs_demand_model_samples.__file__).parent.resolve(strict=True)
        return OSFS(str(path / parse_result.resource))
