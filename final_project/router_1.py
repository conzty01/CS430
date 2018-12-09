"""Router implementation using UDP sockets"""
#!/usr/bin/env python3
# encoding: UTF-8


import os
import random
import select
import struct
import sys
import time
from socket import socket, SOCK_DGRAM, AF_INET

HOST_ID = os.path.splitext(__file__)[0].split("_")[-1]
THIS_NODE = f"127.0.0.{HOST_ID}"
PORT = 4300
MY_PORT = PORT + int(HOST_ID)
NEIGHBORS = set()
# ROUTING_TABLE[destination] = [cost, neighbor to send it to]
ROUTING_TABLE = {}
TIMEOUT = 5
MESSAGES = [
    "Cosmic Cuttlefish",
    "Bionic Beaver",
    "Xenial Xerus",
    "Trusty Tahr",
    "Precise Pangolin"
]
# Done
def read_file(filename: str) -> None:
    """Read config file"""
    with open(filename, "r") as f:
        configStr = f.read()

    routers = configStr.split("\n\n")
    #print(routers)
    for config in routers:
        splitConfig = config.split("\n")
        #print(splitConfig)
        # If we are looking at this node's configuration...
        if splitConfig[0] == THIS_NODE:
            for neighborStat in splitConfig[1:]:
                if neighborStat != "":     # Fixes issue for last router
                    addr, cost = neighborStat.split(" ")
                    NEIGHBORS.add(addr)
                    ROUTING_TABLE[addr] = [int(cost), addr]

    # print("Neighbors:", NEIGHBORS)
    # print("Table:", ROUTING_TABLE)

# Done
def format_update_msg() -> bytearray:
    """Format update message"""
    # Update messages are formed as follows:
    #   1) 0x0 in the first byte
    #   2) next 4 bytes denote a destination address
    #   3) next byte denotes the cost to get to the destination
    #
    #   repeat 2 - 3 for all items in ROUTING_TABLE
    #
    #   For example 127.0.0.1 of cost 10 and to 127.0.0.2 of cost 5:
    #
    #       0x0    0x7f 0x0 0x0 0x1   0xA    0x7f 0x0 0x0 0x2   0x5   ...
    #       type |    127.0.0.1     | cost |     127.0.0.2    | cost  ...

    msg = bytearray()
    msg.append(0x0)

    for dest in ROUTING_TABLE:
        for num in dest.split("."):
            msg.append(int(num))

        msg.append(ROUTING_TABLE[dest][0])

    #print("Update Message:", msg)
    return msg

# Done
def parse_update_msg(msg: bytes) -> list:
    """Parse the given update message"""
    # Update messages are formatted as such:
    #   For example 127.0.0.1 of cost 10 and to 127.0.0.2 of cost 5:
    #
    #       0x0    0x7f 0x0 0x0 0x1   0xA    0x7f 0x0 0x0 0x2   0x5   ...
    #       type |    127.0.0.1     | cost |     127.0.0.2    | cost  ...

    updateList = []
    i = 1   # index
    while i < len(msg) - 1:
        # Get the next address
        #print(msg,i)
        addr = str(msg[i]) + "." + str(msg[i+1]) + "." + str(msg[i+2]) + "." + str(msg[i+3])
        cost = msg[i+4]

        updateList.append((cost,addr))
        i += 5

    return updateList

# Done
def update_table(msg: bytes, neigh_addr: str) -> bool:
    """Update routing table and return 'True' if updated"""

    updateList = parse_update_msg(msg)
    # print(f"Update Message from {neigh_addr} (cost,addr):", updateList)
    # print(f"Current Routing Table:", ROUTING_TABLE)

    changed = False
    for update in updateList:
        cost, dest = update

        # If the destination is in the ROUTING_TABLE
        if dest in ROUTING_TABLE:
            # If the new cost is less than the current cost
            if cost + ROUTING_TABLE[neigh_addr][0] < ROUTING_TABLE[dest][0]:
                # Update the ROUTING_TABLE
                ROUTING_TABLE[dest] = [cost + ROUTING_TABLE[neigh_addr][0], neigh_addr]
                changed = True

        else:   # Add the destination to the ROUTING_TABLE
            if dest != THIS_NODE:
                ROUTING_TABLE[dest] = [cost + ROUTING_TABLE[neigh_addr][0], neigh_addr]
                changed = True

    #print("Updated Table:", changed)
    return changed

# Done
def send_update(dst_node: str) -> None:
    """Send update"""
    sckt = socket(AF_INET, SOCK_DGRAM)
    sckt.bind((THIS_NODE,0))
    dst_port = PORT + int(dst_node.split(".")[-1])

    msg = format_update_msg()
    sckt.sendto(msg, (dst_node, dst_port))


# Done
def format_hello(msg_txt: str, src_node: str, dst_node: str) -> bytearray:
    """Format hello message"""
    msg = bytearray()
    msg.append(0x1)

    for num in src_node.split("."):     # Source IP
        msg.append(int(num))

    for num in dst_node.split("."):         # Dest IP
        msg.append(int(num))

    msg = msg + bytearray(msg_txt.encode())

    return msg


# Done
def parse_hello(msg: bytes, neigh_addr: str) -> str:
    """Calculate the appropriate next hop"""
    shouldForward = True

    sender = str(msg[1]) + "." + str(msg[2]) + "." + str(msg[3]) + "." + str(msg[4])
    destination = str(msg[5]) + "." + str(msg[6]) + "." + str(msg[7]) + "." + str(msg[8])
    data = msg[9:].decode()

    if destination == THIS_NODE:
        shouldForward = False
        print(time.strftime("%H:%M:%S", time.gmtime()) +" | "+ \
            f"Received {data} from {sender}")

    return (shouldForward, data, sender, destination)

# Done
def send_hello(msg_txt: str, src_node: str, dst_node: str) -> None:
    """Send a message"""
    sckt = socket(AF_INET, SOCK_DGRAM)
    sckt.bind((THIS_NODE,0))

    nxtHop = ROUTING_TABLE[dst_node][1]
    hop_port = PORT + int(nxtHop.split(".")[-1])

    msg = format_hello(msg_txt, src_node, dst_node)

    print(time.strftime("%H:%M:%S", time.gmtime()) +" | "+ \
        f"Sending {msg_txt} to {dst_node} via {nxtHop}")

    sckt.sendto(msg,(nxtHop,hop_port))


# Done
def print_status() -> None:
    """Print status of the routing table"""

    print("     {:^14} {:^10} {:^14}".format("Host","Cost","Via"))
    for router in ROUTING_TABLE:
        print("     {:^14} {:^10} {:^14}".format(router,ROUTING_TABLE[router][0],ROUTING_TABLE[router][1]))


def main(args: list):
    """Router main loop"""
    # Read our configuration
    read_file(args[1])

    print(time.strftime("%H:%M:%S", time.gmtime()) +" | "+ "{} here".format(THIS_NODE))

    my_listener = socket(AF_INET, SOCK_DGRAM)
    my_listener.bind((THIS_NODE, MY_PORT))
    print(time.strftime("%H:%M:%S", time.gmtime()) +" | "+ "Binding to {}:{}".format(THIS_NODE, MY_PORT))

    print_status()

    for neighbor in NEIGHBORS:
        send_update(neighbor)

    while True:
        # The following decides when to "randomly" send messages
        #  to other nodes.

        rand = random.randrange(0,10)
        if rand == 5:
            msg = random.choice(MESSAGES)
            dst = random.choice(list(ROUTING_TABLE.keys()))

            send_hello(msg,THIS_NODE,dst)

        elif rand == 1:
            for neighbor in NEIGHBORS:
                send_update(neighbor)

        # Processing Loop

        what_ready = select.select([my_listener], [], [], TIMEOUT)

        for sckt in what_ready[0]:
            msg, addr = sckt.recvfrom(1024)

            if msg[0] == 1:
                # We have a hello_message
                shouldForward, decoded_msg, sender, dest = parse_hello(msg, addr[0])

                if shouldForward:
                    send_hello(decoded_msg, sender, dest)

            elif msg[0] == 0:
                # We have an update_message
                updated = update_table(msg, addr[0])

                if updated:
                    print(time.strftime("%H:%M:%S", time.gmtime()) +" | "+ "Updated table with information from {}".format(addr[0]))
                    print_status()
                    for neighbor in NEIGHBORS:
                        send_update(neighbor)

            # If the flag is not 0 or 1, then we should drop the packet.

if __name__ == "__main__":
    main(sys.argv)
