from flask import Flask, Response
from flask.testing import FlaskClient
from pytest_benchmark.fixture import BenchmarkFixture
from pytest import mark
from typing import Callable, Optional
from ..routes import (
    CurrentCount,
    CurrentTicker,
    UniqueCount,
    UniqueTicker,
    FileType,
    counter,
    ticker,
)
from ..hitcountfile import HitCountBinary


def test_get_counter(benchmark: BenchmarkFixture, client: FlaskClient):
    benchmark(client.get, "/")


def test_home(client: FlaskClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type == "text/html; charset=utf-8"
    assert response.content_length > 0


def test_data(client: FlaskClient):
    response = client.get("/data.json")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.content_length > 0


@mark.parametrize(
    "route,routeFunc",
    [
        ("counter", CurrentCount),
        ("ticker", CurrentTicker),
        ("unique/counter", UniqueCount),
        ("unique/ticker", UniqueTicker),
    ],
)
@mark.parametrize("ext", ["webp", "png", "gif"])
def test_requests(
    app: Flask,
    route: str,
    routeFunc: Callable[[FileType], Response],
    ext: FileType,
):
    with app.test_request_context(f"/{route}.{ext}"):
        response = routeFunc(ext)
        with HitCountBinary("data/hitcount.dat") as data:
            assert response.status_code == 302
            assert response.headers["Location"].endswith(
                f"/{data.count}.{ext}"
            ) or response.headers["Location"].endswith(
                f"/{data.count}-{data.unique}.{ext}"
            )
