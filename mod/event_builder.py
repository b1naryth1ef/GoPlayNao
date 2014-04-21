#!/usr/bin/env python
"""
Builds sourcepawn and python code based on a text file of events
"""
import sys, os, time

BUILD = open("build.txt", "w")

SOURCE_FUNCTION = """
public Action:Event_%s(Handle:event, const String:name[], bool:dontBroadcast) {
    decl String:buffer[2048];
%s
    Format(buffer, sizeof(buffer), "%s,%s"%s
%s);
    LogLine(buffer);
}\n\n
"""

SOURCE_HOOK = """HookEvent("{e.name}", Event_{e.name}, EventHookMode_Post);\n"""

class Event(object):
    def __init__(self, name, attrs):
        self.name = name
        self.attrs = attrs

    def build_pre(self):
        return [attr.build_pre() for attr in self.attrs]

    def build_fmt(self):
        return [attr.build_fmt() for attr in self.attrs]

class Attr(object):
    def __init__(self, name, vtype, desc):
        self.name = name
        self.vtype = vtype
        self.desc = desc

    def build_pre(self):
        result = []

        if self.vtype == "string" or self.vtype == "wstring":
            result.append("    decl String:buff_%s[64];" % self.name)
            result.append('    GetEventString(event, "%s", buff_%s, sizeof(buff_%s));' % (
                self.name, self.name, self.name))

        return "\n".join(result)

    def build_fmt(self):
        if self.vtype in ['string', 'wstring']:
            return '%s', "        buff_%s" % self.name

        if self.vtype in ["int", "short", "byte", "long"]:
            return '%d', '        GetEventInt(event, "%s")' % self.name

        if self.vtype == "float":
            return "%f", '        GetEventFloat(event, "%s")' % self.name

        if self.vtype == "bool":
            return "%d", '        GetEventBool(event, "%s")' % self.name

        print self.vtype

def load_file(f):
    if not os.path.exists(f):
        print "File %s does not exist!" % f
        sys.exit(1)

    return open(f, "r")

def parse_file(f):
    data = f.read()

    events = []
    for event in data.split("\n\n"):
        events.append(parse_event(event))

    return events

def parse_event(data):
    lines = data.split("\n")
    e_name = lines[0].split("Name: ")[1].strip()

    e_attr = []
    for line in lines[2:]:
        data = filter(lambda i: i, line.split(" "))
        typ, name = data[0], data[1]
        desc = ' '.join(data[2:])

        if typ.strip() == "none": continue
        print "%s, %s, %s" % (typ, name, desc)
        e_attr.append(Attr(name.strip(), typ.strip(), desc.strip()))

    return Event(e_name, e_attr)

def dump_sourcepawn(events):
    BUILD.write("SOURCEMOD HOOKS:\n\n")
    for event in events:
        BUILD.write(SOURCE_HOOK.format(e=event))

    BUILD.write("\n\nSOURCEMOD FUNCTIONS:\n\n")
    for id, event in enumerate(events):
        pre = event.build_pre()
        fmt = event.build_fmt()
        #print fmt
        BUILD.write(SOURCE_FUNCTION % (
            event.name,
            "".join(pre),
            id,
            ",".join([i[0] for i in fmt]),
            ',' if len(fmt) else '',
            ",\n".join([i[1] for i in fmt])
        ))

def dump_events(events):
    dump_sourcepawn(events)



if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print "Usage: ./event_builder.py <event_file.html>"
        sys.exit(1)
    events = parse_file(load_file(sys.argv[1   ]))
    dump_events(events)
    BUILD.close()
