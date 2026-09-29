import os

import pytest

os.environ.setdefault("HEADLESS", "1")

from tests.fake_sites import ServedApp, create_qualtrics_app, create_smg_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def quit_pooled_browsers():
    yield
    from survey_automator import get_driver_pool
    for item in get_driver_pool().drivers:
        item["driver"].quit()


@pytest.fixture(scope="session")
def fake_dq_site():
    served = ServedApp(create_smg_app())
    yield served.url
    served.close()


@pytest.fixture(scope="session")
def fake_tims_site():
    served = ServedApp(create_qualtrics_app())
    yield served.url
    served.close()
