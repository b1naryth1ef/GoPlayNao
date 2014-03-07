import socket, thread

class Connection(object):
    def __init__(self, master, conn, addr):
        self.master = master
        self.conn = conn
        self.addr = addr

    def push(self, data):
        print "Sending: `%s`" % data
        self.conn.sendall(data)

    def handle(self):
        while True:
            data = self.conn.recv(2048)
            if not data or not data.strip(): break
            print "Recv: `%s`" % data

            if data.startswith("0"):
                self.push(self.master.data['players'])

        self.conn.close()

class SServer(object):
    def __init__(self, master, host="", port=5595):
        self.master = master
        self.host = host
        self.port = port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.active = False

    def connect(self):
        self.s.bind((self.host, self.port))
        self.s.listen(1)
        self.active = True

    def loop(self):
        while self.active:
            con = Connection(self.master, *self.s.accept())
            thread.start_new_thread(con.handle, ())

def start_server(port, master):
    s = SServer(master, port=port)
    s.connect()
    return s
