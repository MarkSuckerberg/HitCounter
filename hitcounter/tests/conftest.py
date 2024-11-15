from .. import application
from ..hitcountfile import HitCountBinary
from os import remove
from pytest import fixture


@fixture
def app():
    """The flask app."""
    return application


@fixture
def client(app):
    """A flask test client for the app."""
    with app.test_client() as client:
        yield client


@fixture
def file(tmp_path):
    """A HitCountBinary file for use in testing."""
    with HitCountBinary(tmp_path / "test.dat") as file:
        yield file
