from edcr.config import WineHelperConfig
from edcr.platform.input.wine_helper import WineHelperClient


def unexpected(*args, **kwargs):
    raise AssertionError('Unexpected wine helper dependency used')


def helper_client(config=WineHelperConfig(), **dependencies):
    defaults = dict(connect=unexpected, sleeper=unexpected, clock=unexpected,
                    popen=unexpected, process_table=unexpected, read_token=unexpected)
    defaults.update(dependencies)
    return WineHelperClient(config, **defaults)
