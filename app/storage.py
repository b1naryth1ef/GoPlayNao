import os, uuid

class StorageEngine(object):
    def __init__(self, dir="."):
        self.dir = dir
        self.path = os.path.join(self.dir, "files")
        if not os.path.exists(self.path):
            os.mkdir(self.path)

    def storeFile(self, data):
        id = str(uuid.uuid4())
        path = os.path.join(self.path, id)

        with open(path, "w") as f:
            f.write(data)

        return id

    def getFilePath(self, id):
        path = os.path.join(self.path, str(id))

        if not os.path.exists(path):
            raise IOError("No file with id `%s`" % id)

        return path

    def getFile(self, id):
        return open(self.getFilePath(id), "r")


STORAGE = StorageEngine()
