import maddenmode


def test_version() -> None:
    # the format and the single source are checked in test_about.py; this only
    # guards that the package exposes a version at all
    assert isinstance(maddenmode.__version__, str)
    assert maddenmode.__version__
