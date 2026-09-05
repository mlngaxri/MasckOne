import pytest

from masck_one.authority import load_authority
from masck_one.cleanser_service_envelope import build_complete_cleanser_module_service_envelope
from masck_one.cleanser_service_interfaces import build_cleanser_service_geometry
from masck_one.model import build_model
from masck_one.realized_cleanser_storage import build_realized_cleanser_storage


@pytest.fixture(scope="session")
def cell4_authority():
    return load_authority()


@pytest.fixture(scope="session")
def cell4_model(cell4_authority):
    return build_model(cell4_authority)


@pytest.fixture(scope="session")
def cell4_cleanser_storage(cell4_authority):
    return build_realized_cleanser_storage(cell4_authority)


@pytest.fixture(scope="session")
def cell4_cleanser_service(cell4_authority):
    return build_cleanser_service_geometry(cell4_authority)


@pytest.fixture(scope="session")
def cell4_cleanser_service_envelope(cell4_authority):
    return build_complete_cleanser_module_service_envelope(cell4_authority)
