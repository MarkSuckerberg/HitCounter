from random import randint
from ..hitcountfile import (
    HitCountFile,
    HitCountJson,
    HitCountBinary,
    HitCountPickle,
    COUNT_SIZE,
    CURRENT_VERSION,
)
from pathlib import Path
from pytest import mark
from hashlib import blake2s


@mark.parametrize("fileType", [HitCountBinary, HitCountJson, HitCountPickle])
def test_store(fileType: type[HitCountFile], tmp_path: Path):
    data = {}
    with fileType(tmp_path / "hits.dat") as file:
        data["count"] = file.count
        data["unique"] = file.unique
        data["visitors"] = file.GetVisitors()

        file.NewVisitor(str(randint(1, 100)))

        assert file.count == data["count"] + 1
        assert file.unique == data["unique"] + 1

        data["count"] = file.count
        data["unique"] = file.unique
        data["visitors"] = file.GetVisitors()

    with fileType(tmp_path / "hits.dat") as file:
        assert file.count == data["count"]
        assert file.unique == data["unique"]
        assert file.GetVisitors() == data["visitors"]

        visitor = str(randint(101, 200))
        assert not file.NewVisitor(visitor)
        assert file.unique == data["unique"] + 1

        # Make sure the same visitor is not added again
        assert file.NewVisitor(visitor)
        assert file.unique == data["unique"] + 1


def test_update(tmp_path: Path):
    with open(tmp_path / "hits.dat", "xb") as file:
        file.write(int(50).to_bytes(COUNT_SIZE))
        file.write(int(10).to_bytes(COUNT_SIZE))
        file.write(blake2s(b"").digest())

    with HitCountBinary(tmp_path / "hits.dat") as file:
        assert file.count == 50
        assert file.unique == 10

        file.NewVisitor("test")

        visitors = file.GetVisitors()
        assert len(visitors) == 2
        assert blake2s(b"").digest() in visitors
        assert blake2s(b"test").digest() in visitors

    with HitCountBinary(tmp_path / "hits.dat") as file:
        assert file.version == CURRENT_VERSION
        assert file.count == 51
        assert file.unique == 11
