import pooch
from ._reader import read_oct


def _download_sample(url: str, known_hash: str, filename: str) -> str:
    """Download sample file via pooch and return local cached path

    Args:
        url (str): Web URL of sample data
        known_hash (str): File fingerprint (checksum)
        filename (str): Filename under which to store the local file

    Returns:
        str: Local cached path from fetched file
    """
    return pooch.retrieve(
        url=url, known_hash=known_hash, fname=filename, path=pooch.os_cache("bio_oct")
    )


def load_sample_membrane_w_spacer():
    path = _download_sample(
        url="https://zenodo.org/records/20758173/files/membrane_w_spacer.oct",
        known_hash="md5:becdd6f0cb1bd7007733c9beadb16ccf",
        filename="membrane_w_spacer.oct",
    )
    return read_oct(path)


def load_sample_rough_electrode():
    path = _download_sample(
        url="https://zenodo.org/records/20758173/files/rough_electrode.oct",
        known_hash="md5:249012dcf14a87bd07ccd385c6387c8a",
        filename="rough_electrode.oct",
    )
    return read_oct(path)


def load_sample_smooth_electrode_shadowed():
    path = _download_sample(
        url="https://zenodo.org/records/20758173/files/smooth_electrode_shadowed.oct",
        known_hash="md5:206d72cba6abadfcc9df2997b57e5123",
        filename="smooth_electrode_shadowed.oct",
    )
    return read_oct(path)
