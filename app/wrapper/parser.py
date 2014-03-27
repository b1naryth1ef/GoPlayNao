import logging, sqlite3

log = logging.getLogger(__file__)

class GameParser(object):
    """
    Rev 1 game parser
    """
    def __init__(self, id):
        self.db = sqlite3.connect("log_%s.db" % id)

    def handle(self, packet):
        args = packet.split(",")
        if not len(args):
            log.error("Recieved unparseable packet: %s", packet)
            return

        if not args[0].isdigit():
            log.error("First attribute in packet is not an integer: %s", packet)
            return

        if hasattr(self, "packet_%s" % args[0]):
            return getattr(self, "packet_%s" % args[0])(args[1:])
