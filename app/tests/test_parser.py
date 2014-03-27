from wrapper.parser import GameParser

p = GameParser(1)

with open("test_parser.txt") as f:
    for line in f.readlines():
        p.handle(line)
