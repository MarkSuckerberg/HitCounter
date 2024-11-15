from hashlib import blake2s as hash
import fcntl
import json
import pickle
from shutil import copyfile
from os import getenv, PathLike
from io import BufferedRandom, TextIOWrapper


class HitCountFile:
    count: int
    unique: int
    file: BufferedRandom | TextIOWrapper

    def __init__(self, fileName: str | bytes | PathLike):
        try:
            # If it doesn't exist, we know it's already empty
            self.file = open(fileName, "xb+")

            fcntl.flock(self.file, fcntl.LOCK_EX)

            self.Defaults()
            return
        except FileExistsError:
            pass

        # Open the file for reading
        self.file = open(fileName, "rb+")

        fcntl.flock(self.file, fcntl.LOCK_EX)

        self.PostInit()

    def Defaults(self):
        """Sets the default values for the file."""
        self.count = int(getenv("INITIAL_COUNT") or 0)
        self.unique = int(getenv("INITIAL_UNIQUE_COUNT") or 0)

    def PostInit(self):
        """Called after the file is successfully loaded. Override this to load the data."""
        pass

    def Close(self):
        """Closes the file and releases the lock. Do not override this, override PreClose instead."""
        self.PreClose()

        # Release the lock
        fcntl.flock(self.file, fcntl.LOCK_UN)

        # Close the file
        self.file.close()

    def NewVisitor(self, visitor: str) -> bool:
        """Adds a new visitor to the file. Returns True if the visitor already exists."""
        return True

    def GetVisitors(self) -> set[bytes]:
        """Returns the full set of visitors stored in the file."""
        return set()

    def PreClose(self):
        """Called before the file is closed. Override this to save the data."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.Close()


class HitCountJson(HitCountFile):
    visitors: set[str]
    file: TextIOWrapper

    def __init__(self, fileName):
        try:
            # If it doesn't exist, we know it's already empty
            self.file = open(fileName, "x+")

            fcntl.flock(self.file, fcntl.LOCK_EX)

            self.Defaults()
            self.visitors = set()
            return
        except FileExistsError:
            pass

        # Open the file for reading
        self.file = open(fileName, "r+")

        self.PostInit()

    def PostInit(self):

        fcntl.flock(self.file, fcntl.LOCK_EX)

        try:
            data = json.load(self.file)
        except json.JSONDecodeError:
            self.Defaults()
            copyfile(self.file.name, self.file.name + ".err")
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
        return False

    def GetVisitors(self):
        bytesVisitor = []
        for visitor in self.visitors:
            bytesVisitor.append(bytes.fromhex(visitor))
        return bytesVisitor

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
    file: BufferedRandom

    def PostInit(self):
        try:
            data = pickle.load(self.file)
        except pickle.UnpicklingError:
            self.Defaults()
            copyfile(self.file.name, self.file.name + ".err")
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
        return False

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


COUNT_SIZE = 4
VISITOR_SIZE = hash().digest_size

COUNT_OFFSET = 0
UNIQUE_COUNT_OFFSET = COUNT_OFFSET + COUNT_SIZE
VERSION_OFFSET = UNIQUE_COUNT_OFFSET + COUNT_SIZE

# Leave padding for further data to be added
VISITORS_ARRAY_OFFSET = VISITOR_SIZE

# Don't somehow accidentally overlap the data
assert VISITORS_ARRAY_OFFSET > (VERSION_OFFSET + COUNT_SIZE)

VERSION = "v1.1.0"
CURRENT_VERSION = int(VERSION[1:].split(".")[1])


class HitCountBinary(HitCountFile):
    version: int
    file: BufferedRandom

    def PostInit(self):
        # Read the initial values
        self.count = int.from_bytes(self.file.read(COUNT_SIZE))
        self.unique = int.from_bytes(self.file.read(COUNT_SIZE))
        self.version = int.from_bytes(self.file.read(COUNT_SIZE))

        if not self.HandleUpdate(self.version):
            copyfile(self.file.name, self.file.name + ".err")
            self.Defaults()

    def HandleUpdate(self, version: int):
        """Handles updating the file to the current version. Returns True if the file was successfully updated."""
        if version == CURRENT_VERSION:
            return True

        copyfile(self.file.name, f"{self.file.name}.{version}.bak")

        # Pre-version 1, it might be 0 or the first part of the first visitor
        if version == 0 or version > CURRENT_VERSION:
            self.version = 1
            self.file.seek(VERSION_OFFSET)
            visitors = self.GetVisitors(False)

            self.file.seek(VISITORS_ARRAY_OFFSET)
            for visitor in visitors:
                self.file.write(visitor)

            self.file.seek(VERSION_OFFSET)
            self.file.write(CURRENT_VERSION.to_bytes(COUNT_SIZE))
            self.file.write(
                b"\x00" * (VISITORS_ARRAY_OFFSET - VERSION_OFFSET - COUNT_SIZE)
            )

            return True

        return False

    def PreClose(self):
        # Move to the start of the file
        self.file.seek(COUNT_OFFSET)

        # Write the count and unique count
        self.file.write(self.count.to_bytes(COUNT_SIZE))
        self.file.write(self.unique.to_bytes(COUNT_SIZE))
        self.file.write(CURRENT_VERSION.to_bytes(COUNT_SIZE))

    def GetVisitors(self, seek=True):
        if seek:
            self.file.seek(VISITORS_ARRAY_OFFSET)

        visitors: set[bytes] = set()
        while True:
            read = self.file.read(VISITOR_SIZE)
            if read == b"":
                return visitors

            visitors.add(read)

    def NewVisitor(self, visitor: str):
        self.count += 1

        self.file.seek(VISITORS_ARRAY_OFFSET)
        visitorHash = hash(visitor.encode()).digest()
        while True:
            read = self.file.read(VISITOR_SIZE)
            if read == b"":
                arraySize = self.file.tell() - VISITORS_ARRAY_OFFSET

                # Add padding if necessary
                if arraySize % VISITOR_SIZE != 0:
                    self.file.write((arraySize % VISITOR_SIZE) * b"\x00")

                self.file.write(visitorHash)
                self.unique += 1
                return False
            if read == visitorHash:
                return True


class HitCountBinarySimple(HitCountFile):
    """A simpler and faster version that just stores hits. Compatible with the normal version."""

    file: BufferedRandom

    def PostInit(self):
        # Read the initial values
        self.count = int.from_bytes(self.file.read(COUNT_SIZE))
        self.unique = 0

    def PreClose(self):
        # Move to the start of the file
        self.file.seek(COUNT_OFFSET)

        # Write the count and unique count
        self.file.write(self.count.to_bytes(COUNT_SIZE))
