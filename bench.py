from hitcount_file import HitCountJson, HitCountBinary, HitCountPickle
from random import randint
from pyperf import Runner
from routes import GenerateAnimated, GenerateTicker, GenerateTickerUnique
import hashlib


def Json():
    with HitCountJson(f"data/bench/{randint(1,5)}.json") as file:
        file.NewVisitor(str(randint(1, 100)))

        data = {}

        data["count"] = file.count
        data["unique"] = file.unique
        data["visitors"] = file.GetVisitors()


def Binary():
    with HitCountBinary(f"data/bench/{randint(1,5)}.bin") as file:
        file.NewVisitor(str(randint(1, 100)))

        data = {}

        data["count"] = file.count
        data["unique"] = file.unique
        data["visitors"] = file.GetVisitors()


def Pickle():
    with HitCountPickle(f"data/bench/{randint(1,5)}.pkl") as file:
        file.NewVisitor(str(randint(1, 100)))

        data = {}

        data["count"] = file.count
        data["unique"] = file.unique
        data["visitors"] = file.GetVisitors()


def Blake(digest: int, salt: int = 0):
    if salt > 0:
        hashlib.blake2s(
            randint(1, 1000000).to_bytes(16), digest_size=digest, salt=salt.to_bytes(8)
        )
    else:
        hashlib.blake2s(randint(1, 1000000).to_bytes(16), digest_size=digest)


if __name__ == "__main__":
    runner = Runner()
    runner.bench_func("Ticker", GenerateTicker, randint(1, 1000000))
    runner.bench_func(
        "Ticker with Unique",
        GenerateTickerUnique,
        randint(1, 1000000),
        randint(1, 1000000),
    )
    runner.bench_func("Animated", GenerateAnimated, randint(1, 1000000))

    runner.bench_func("JSON", Json)
    runner.bench_func("Pickle", Pickle)
    runner.bench_func("Bin", Binary)
