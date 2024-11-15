from ..hitcountfile import (
    HitCountFile,
    HitCountJson,
    HitCountBinary,
    HitCountPickle,
    HitCountBinarySimple,
)
from ..routes import GenerateAnimated, GenerateTicker, GenerateTickerUnique
from random import randint
from pytest import mark
from pytest_benchmark.fixture import BenchmarkFixture
from pathlib import Path


@mark.parametrize(
    "store", [HitCountBinary, HitCountJson, HitCountPickle, HitCountBinarySimple]
)
def test_bench(benchmark: BenchmarkFixture, tmp_path: Path, store: HitCountFile):
    benchmark(StoreBench, store, tmp_path / "test.dat")


def StoreBench(fileType: type[HitCountFile], tmp_path: Path):
    data = {}
    with fileType(tmp_path) as file:
        data["count"] = file.count
        data["unique"] = file.unique
        data["visitors"] = file.GetVisitors()

        file.NewVisitor(str(randint(1, 100)))


def test_generate_ticker(benchmark: BenchmarkFixture):
    benchmark(GenerateTicker, randint(1, 1000000))


def test_generate_ticker_unique(benchmark: BenchmarkFixture):
    benchmark(GenerateTickerUnique, randint(1, 1000000), randint(1, 1000000))


def test_generate_animated(benchmark: BenchmarkFixture):
    benchmark(GenerateAnimated, randint(1, 1000000))
