import socket, thread, json

class Server(object):
    def __init__(self, host="", port=5595):
        self.host = host
        self.port = port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.active = False

    def push(self, conn, obj):
        conn.sendall(json.dumps(obj))

    def getPacket(self, id):
        if hasattr(self, "packet_%s" % id):
            return getattr(self, "packet_%s" % id)
        return None

    def handle(self, conn, addr):
        while True:
            data = conn.recv(2048)
            if not data or not data.strip(): break

            try:
                obj = json.loads(data.strip())
            except:
                print "Error decoding data: `%s`" % data
                break

            if 'id' in obj:
                self.getPacket(obj['id'])(conn, obj)

        conn.close()

    def connect(self):
        self.s.bind((self.host, self.port))
        self.s.listen(1)
        self.active = True

    def loop(self):
        while self.active:
            conn, addr = self.s.accept()
            thread.start_new_thread(self.handle, (conn, addr))

    def packet_0(self, conn, data):
        self.push(conn, {"success": True, "msg": "YOLO SWAG!"})

s = Server()
s.connect()
try:
    s.loop()
except:
    s.s.close()