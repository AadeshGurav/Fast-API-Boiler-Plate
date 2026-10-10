"""Print the first TCP port >= the given one that nothing is listening on.

Used by `make setup` so the Docker services never collide with a MongoDB/Redis already
running on the machine (the app would silently talk to the wrong server).
"""

import socket
import sys


def is_free(port: int) -> bool:
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family) as probe:
                if probe.connect_ex((host, port)) == 0:
                    return False
        except OSError:
            continue  # no IPv6 here
    return True


port = int(sys.argv[1])
while not is_free(port):
    port += 1
print(port)
