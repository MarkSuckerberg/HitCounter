from hitcount_file import HitCountJson, HitCountBinary, HitCountPickle
from random import randint
from pyperf import Runner


def Json():
    with HitCountJson("data/bench.json") as file:
        file.NewVisitor(str(randint(1, 100)))

        data = {}

        data["count"] = file.count
        data["unique"] = file.unique
        data["visitors"] = file.GetVisitors()


def Binary():
    with HitCountBinary("data/bench.bin") as file:
        file.NewVisitor(str(randint(1, 100)))

        data = {}

        data["count"] = file.count
        data["unique"] = file.unique
        data["visitors"] = file.GetVisitors()


def Pickle():
    with HitCountPickle("data/bench.pkl") as file:
        file.NewVisitor(str(randint(1, 100)))

        data = {}

        data["count"] = file.count
        data["unique"] = file.unique
        data["visitors"] = file.GetVisitors()

if __name__ == "__main__":
    runner = Runner()
    runner.bench_func("JSON", Json)
    runner.bench_func("Pickle", Pickle)
    runner.bench_func("Bin", Binary)
