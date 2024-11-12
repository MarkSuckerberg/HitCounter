from hashlib import blake2s as hash
from io import BufferedRandom
import fcntl
import json
import pickle
from shutil import copyfile
from os import getenv

COUNT_SIZE = 4
VISITOR_SIZE = hash().digest_size

COUNT_OFFSET = 0
UNIQUE_COUNT_OFFSET = COUNT_OFFSET + COUNT_SIZE
VISITORS_ARRAY_OFFSET = UNIQUE_COUNT_OFFSET + COUNT_SIZE


class HitCountFile:
    count: int
    unique: int
    file: BufferedRandom

    def __init__(self, fileName: str):
        try:
            # If it doesn't exist, we know it's already empty
            self.file = open(fileName, "xb+")

            fcntl.flock(self.file, fcntl.LOCK_EX)

            self.count = int(getenv("INITIAL_COUNT") or 0)
            self.unique = 0
            return
        except FileExistsError:
            pass

        # Open the file for reading
        self.file = open(fileName, "rb+")

        fcntl.flock(self.file, fcntl.LOCK_EX)

        self.PostInit()

    def PostInit(self):
        pass

    def Close(self):
        self.PreClose()

        # Release the lock
        fcntl.flock(self.file, fcntl.LOCK_UN)

        # Close the file
        self.file.close()

    def NewVisitor(self, visitor: str):
        pass

    def GetVisitors(self):
        pass

    def PreClose(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.Close()


class HitCountJson(HitCountFile):
    visitors: set[str] = set()

    def __init__(self, fileName):
        try:
            # If it doesn't exist, we know it's already empty
            self.file = open(fileName, "x+")

            fcntl.flock(self.file, fcntl.LOCK_EX)

            self.count = int(getenv("INITIAL_COUNT") or 0)
            self.unique = 0
            return
        except FileExistsError:
            pass

        # Open the file for reading
        self.file = open(fileName, "r+")

        fcntl.flock(self.file, fcntl.LOCK_EX)

        try:
            data = json.load(self.file)
        except json.JSONDecodeError:
            self.count = int(getenv("INITIAL_COUNT") or 0)
            self.unique = 0
            copyfile(fileName, fileName + ".err")
            return

        self.count = data["count"]
        self.unique = data["unique"]
        self.visitors = set(data["visitors"])

    def NewVisitor(self, visitor: str):
        self.count += 1
        visitorHash = hash(visitor.encode()).hexdigest()
        if visitorHash in self.visitors:
            return True
        self.unique += 1
        self.visitors.add(visitorHash)

    def GetVisitors(self):
        return self.visitors

    def PreClose(self):
        data = {
            "count": self.count,
            "unique": self.unique,
            "visitors": list(self.visitors),
        }

        self.file.seek(0)
        json.dump(data, self.file)


class HitCountPickle(HitCountFile):
    visitors: set[bytes] = set()

    def PostInit(self):
        try:
            data = pickle.load(self.file)
        except pickle.UnpicklingError:
            return

        self.count = data["count"]
        self.unique = data["unique"]
        self.visitors = data["visitors"]

    def NewVisitor(self, visitor: str):
        self.count += 1

        visitorHash = hash(visitor.encode()).digest()
        if visitorHash in self.visitors:
            return True
        self.unique += 1
        self.visitors.add(visitorHash)

    def GetVisitors(self):
        return self.visitors

    def PreClose(self):
        data = {
            "count": self.count,
            "unique": self.unique,
            "visitors": self.visitors,
        }

        self.file.seek(0)
        self.file.truncate(0)

        pickle.dump(data, self.file)


class HitCountBinary(HitCountFile):
    def PostInit(self):
        # Read the initial values
        self.count = int.from_bytes(self.file.read(COUNT_SIZE))
        self.unique = int.from_bytes(self.file.read(COUNT_SIZE))

    def PreClose(self):
        # Move to the start of the file
        self.file.seek(0)

        # Write the count and unique count
        self.file.write(self.count.to_bytes(COUNT_SIZE))
        self.file.write(self.unique.to_bytes(COUNT_SIZE))

    def GetVisitors(self):
        visitors = []
        while True:
            read = self.file.read(VISITOR_SIZE)
            if read == b"":
                return visitors

            visitors.append(read.hex())

    def NewVisitor(self, visitor: str):
        self.count += 1

        self.file.seek(VISITORS_ARRAY_OFFSET)
        visitorHash = hash(visitor.encode()).digest()
        while True:
            read = self.file.read(VISITOR_SIZE)
            if read == b"":
                arraySize = self.file.tell() - VISITORS_ARRAY_OFFSET
                if arraySize % VISITOR_SIZE != 0:
                    self.file.write((arraySize % VISITOR_SIZE) * b"\x00")
                self.file.write(visitorHash)
                self.unique += 1
                return False
            if read == visitorHash:
                return True
