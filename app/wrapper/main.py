from multiprocessing import Process
from sockserver import start_server
import redis, os, json, subprocess

r = redis.Redis(host=os.getenv("REDIS_HOST"), password=os.getenv("REDIS_PASS"))

SOCKET_OFFSET = 5000

class Master(object):
    def __init__(self, ids=[]):
        self.ids = ids
        self.servers = []

    def spawn_all(self):
        for id in self.ids:
            s = Server(id)
            s.proc = Process(target=s.run)
            self.servers.append(s)

class Server(object):
    def __init__(self, id, path="", ip="", port=""):
        global SOCKET_OFFSET
        self.id = id
        self.ip = ip
        self.port = port
        self.path = path
        self.args = []

        self.proc = None
        SOCKET_OFFSET += 1
        self.server = start_server(SOCKET_OFFSET, self)

        self.match = None

    def spawn(self):
        self.proc = subprocess.Popen(self.path + ' ' + ' '.join(self.args),
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE)
        self.proc.start()

    def kill(self):
        self.proc.kill()
        self.proc = None

    def handle(self, data):
        if data['tag'] == "match":
            self.match = data
            if self.proc:
                print "Something is wrong, master wants to spawn new process, but we're running?!"
            self.args = [
                "-game csgo",
                "-console",
                "-usercon",
                "+ip %s" % self.ip,
                "-tickrate 128",
                "-port %s" % self.port,
                "-maxplayers 12",
                "+game_type 0",
                "+game_mode 1",
                "+map %s" % data['map'],
                "+exec server.cfg",
                "+hostname GoPlayMM #%s" % self.id
            ]

    def run(self):
        ps = r.pubsub()
        ps.subscribe("server-%s" % self.id)

        for item in ps.listen():
            if item['type'] == "message":
                self.handle(json.loads(item['data']))
