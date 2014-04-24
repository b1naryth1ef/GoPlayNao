import logging
# from achievement import handle_one
from packet_index import PACKET_INDEX
from ..util import convert_steamid

log = logging.getLogger(__file__)

class Event(object):
    def __init__(self, parser, args):
        self.parser = parser
        self.id = args[0]

        self.config = PACKET_INDEX[int(self.id)]
        for index, val in enumerate(args):
            setattr(self, self.config['attrs'][index], val)

    def to_json(self):
        data = {
            "id": self.id,
            "data": {k: getattr(self, k) for k in self.config['attrs']}
        }
        if self.has_user():
            data['user'] = self.parser.user_index.get(self.userid)
        return data

    def has_user(self):
        return ('userid' in self.__dict__.keys())

    def dispatch(self):
        if hasattr(self.parser, self.config.get("name")):
            getattr(self.parser, self.config.get("name"))(self)

class GameParser(object):
    """
    Rev 1 game parser
    """
    def __init__(self, parent, id):
        self.parent = parent

        self.round = 0
        self.user_index = {}
        self.log = []

    def handle(self, packet):
        args = packet.split(",")
        if not len(args):
            log.error("Recieved unparseable packet: %s", packet)
            return

        log.debug("Got packet: %s", args[0])
        if not args[0].isdigit():
            log.error("First attribute in packet is not an integer: %s", packet)
            return

        if hasattr(self, "packet_%s" % args[0]):
            getattr(self, "packet_%s" % args[0])()

        if args[0] in PACKET_INDEX:
            eve = Event(self, args)
            eve.dispatch()
            self.log.append(eve.to_json())

    def player_connect(self, event):
        self.user_index[event.userid] = convert_steamid(event.networkid)

    def player_disconnect(self, event): pass

    def round_start(self, event):
        self.round += 1

    def packet_9999(self, packet):
        log.info("Got game-end packet!")
        self.parent.end(self.log)
