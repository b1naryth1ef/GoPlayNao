from multiprocessing import Process
from sockserver import start_server
import redis, os, json, subprocess, logging, random, thread

r = redis.Redis(host=os.getenv("REDIS_HOST"), password=os.getenv("REDIS_PASS"))
log = logging.getLogger(__file__)

SOCKET_OFFSET = random.randint(5000, 7000)
BASE_PATH = "/root/steam/SteamApps/common/Counter-Strike Global Offensive Beta - Dedicated Server/"

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
        self.sockport = SOCKET_OFFSET
        self.server = start_server(self.sockport, self)

        self.match = None

        self.run()

    def upload(self, i): pass

    # TODO: upload demo and sql db
    def endMatch(self):
        self.kill()

        DEMO_PATH = os.path.join(BASE_PATH, "csgo", "match_%s.dem" % self.match['id'])
        DB_PATH = "log_%s.db" % self.match['id']

        self.upload(DEMO_PATH)
        self.upload(DB_PATH)

    def debug(self, r):
        while True:
            data = r.read()
            if not data: break
            print ">> %s" % data

    def spawn(self):
        self.proc = subprocess.Popen(self.path + ' ' + ' '.join(self.args),
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE)
        thread.start_new_thread(self.debug, (self.proc.stdout, ))
        thread.start_new_thread(self.debug, (self.proc.stderr, ))

    def kill(self):
        self.proc.kill()
        self.proc = None

    def handle(self, data):
        if data['tag'] == "match":
            self.match = data
            if self.proc:
                log.error("We got a new match packet, but a process is already running!")
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
                "+map %s" % self.match['map'],
                "+exec server.cfg",
                "+hostname 'GoPlayMM #%s'" % self.id,
                "+gp_players '%s'" % self.match['players'],
                "+gp_port '%s'" % self.sockport,
                "+gp_teama '%s'" % self.match['teama'],
                "+gp_teamb '%s'" % self.match['teamb'],
                "+gp_matchid %s" % self.match['id']
            ]
            self.spawn()

    def run(self):
        ps = r.pubsub()
        ps.subscribe("server-%s" % self.id)

        for item in ps.listen():
            if item['type'] == "message":
                self.handle(json.loads(item['data']))

if __name__ == '__main__':
    # TEMP, FIXME, need a config here
    os.chdir(BASE_PATH)
    Server(1,
        path="./srcds_linux",
        ip="0.0.0.0",
        port="27015")
