import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Tuple
from urllib.parse import urlencode

from fs import copy, open_fs
from fs.base import FS
from fs.errors import NoSysPath
from fs.opener.parse import parse_fs_url
from fs.osfs import OSFS

from cs_demand_model.datastore import DataStore
from cs_demand_model.datastore._fs import FSDataStore
from cs_demand_model.datastore._zip import ZipDataStore

logger = logging.getLogger(__name__)


def fs_datastore(fs_url) -> DataStore:
    # Url can be a valid filesystem url or a filesystem url + a filename
    fs, file = _fs_from_url(fs_url)
    if file is None:
        return FSDataStore(fs)
    return create_zip_store(fs, file)


def _fs_from_url(fs_url: str) -> Tuple[FS, str | None]:
    """
    Convert a filesystem url to a filesystem object
    """
    if "://" not in fs_url:
        fs_url = f"osfs://{fs_url}"

    try:
        return open_fs(fs_url), None
    except:
        pass

    parse_result = parse_fs_url(fs_url)
    if parse_result.params:
        qs = "?" + urlencode(parse_result.params)
    else:
        qs = ""

    if "/" in parse_result.resource:
        path, file = fs_url.rsplit("/", 1)
        return open_fs(f"{path}{qs}"), parse_result.resource.rsplit("/", 1)[1]
    else:
        path, file = fs_url.rsplit("://", 1)
        return open_fs(f"{path}://{qs}"), parse_result.resource


def create_zip_store(path: FS, file: str) -> DataStore:
    try:
        syspath = path.getsyspath(file)
        return ZipDataStore(syspath)
    except NoSysPath:
        pass

    return TmpZipDataStore(path, file)


class TmpZipDataStore(ZipDataStore):
    """
    Simply a wrapper around the ZipDataStore class that ensures the tmpfile is deleted
    when the object is deleted
    """

    def __init__(self, path: FS, file: str):
        self.__tmpdir = tmpdir = TemporaryDirectory()
        dest_fs = OSFS(tmpdir.name)
        logger.warning(
            "Network zip access not possible. Copying %s to %s", file, tmpdir.name
        )
        copy.copy_file(path, file, dest_fs, file)
        super().__init__(Path(tmpdir.name) / file)
