"""Python Pinger"""
#!/usr/bin/env python3
# encoding: UTF-8

import binascii
import os
import select
import struct
import sys
import time
import socket
from statistics import mean, stdev

ECHO_REQUEST_TYPE = 8
ECHO_REPLY_TYPE = 0
ECHO_REQUEST_CODE = 0
ECHO_REPLY_CODE = 0
REGISTRARS = ["afrinic.net", "apnic.net", "arin.net", "lacnic.net", "ripe.net"]
# REGISTRARS = ["example.com"]


def print_raw_bytes(pkt: bytes) -> None:
    """Printing the packet bytes"""
    for i in range(len(pkt)):
        sys.stdout.write("{:02x} ".format(pkt[i]))
        if (i + 1) % 16 == 0:
            sys.stdout.write("\n")
        elif (i + 1) % 8 == 0:
            sys.stdout.write("  ")
    sys.stdout.write("\n")


def checksum(pkt: bytes) -> int:
    """Calculate checksum"""
    csum = 0
    count = 0
    count_to = (len(pkt) // 2) * 2

    while count < count_to:
        this_val = (pkt[count + 1]) * 256 + (pkt[count])
        csum = csum + this_val
        csum = csum & 0xFFFFFFFF
        count = count + 2

    if count_to < len(pkt):
        csum = csum + (pkt[len(pkt) - 1])
        csum = csum & 0xFFFFFFFF

    csum = (csum >> 16) + (csum & 0xFFFF)
    csum = csum + (csum >> 16)
    result = ~csum
    result = result & 0xFFFF
    result = result >> 8 | (result << 8 & 0xFF00)

    return result


def bytes_to_val(bytes_lst: list) -> int:
    '''Merge 2 bytes into a value'''
    res = 0
    for num,pos in enumerate(range(len(bytes_lst),0,-1)):
        res += bytes_lst[pos-1] << (8*num)

    return res


def parse_reply(
    my_socket: socket.socket, req_id: int, timeout: int, addr_dst: str
) -> tuple:
    """Receive an Echo reply"""
    time_left = timeout
    while True:
        started_select = time.time()
        what_ready = select.select([my_socket], [], [], time_left)
        how_long_in_select = time.time() - started_select
        if what_ready[0] == []:  # Timeout
            raise TimeoutError("Request timed out after 1 sec")

        time_rcvd = time.time()
        pkt_rcvd, addr = my_socket.recvfrom(1024)
        if addr[0] != addr_dst:
            raise ValueError(f"Wrong sender: {addr[0]}")

        # Extract ICMP header from the IP packet and parse it
        #print_raw_bytes(pkt_rcvd)

        if pkt_rcvd[20] != 0:
            raise ValueError(f"Invalid Ping Type: {pkt_rcvd[20]}")
        else:
            length = bytes_to_val(pkt_rcvd[2:4])
            ttl = pkt_rcvd[8]
            return (length,ttl)

        # DONE: End of ICMP parsing
        time_left = time_left - how_long_in_select
        if time_left <= 0:
            raise TimeoutError("Request timed out after 1 sec")


def format_request(req_id: int, seq_num: int) -> bytes:
    """Format an Echo request"""
    my_checksum = 0
    header = struct.pack(
        "bbHHh", ECHO_REQUEST_TYPE, ECHO_REQUEST_CODE, my_checksum, req_id, seq_num
    )
    data = struct.pack("d", time.time())
    my_checksum = checksum(header + data)

    if sys.platform == "darwin":
        my_checksum = socket.htons(my_checksum) & 0xFFFF
    else:
        my_checksum = socket.htons(my_checksum)

    header = struct.pack(
        "bbHHh", ECHO_REQUEST_TYPE, ECHO_REQUEST_CODE, my_checksum, req_id, seq_num
    )
    packet = header + data
    return packet


def send_request(addr_dst: str, seq_num: int, timeout: int = 1) -> tuple:
    """Send an Echo Request"""
    result = None
    proto = socket.getprotobyname("icmp")
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, proto)
    my_id = os.getpid() & 0xFFFF

    packet = format_request(my_id, seq_num)
    my_socket.sendto(packet, (addr_dst, 1))

    try:
        result = parse_reply(my_socket, my_id, timeout, addr_dst)
    except ValueError as ve:
        print(f"Packet error: {ve}")
    finally:
        my_socket.close()
    return result


def ping(host: str, pkts: int, timeout: int = 1) -> None:
    """Main loop"""
    # TODO: Implement the main loop

    ip = socket.gethostbyname(host)
    print(f"\n--- Ping {host} ({ip}) using Python ---\n")

    numTrans = 0
    numRec = 0
    for req_id in range(pkts):
        seq_id = (req_id + 1) * 0x01
        reqBytes = format_request(req_id, seq_id)

        try:
            numTrans += 1
            startTime = time.time()
            length, ttl = send_request(ip, seq_id, timeout)
            timePassed = time.time() - startTime
            numRec += 1

            print(f"{length} bytes from {ip}: icmp_seq={req_id+1} TTL={ttl} time={(timePassed*1000):.2f} ms")

        except TimeoutError:
            print(f"No response: Request timed out after {timeout} sec")

    print(f"\n--- {host} ping statistics ---")

    if numRec == 0:
        percent = 100
    else:
        percent = (numTrans - numRec) / numTrans

    print(f"{numTrans} packets transmitted, {numRec} recevied, {percent:.2f}% packet loss")

    # DONE
    return


if __name__ == "__main__":
    for rir in REGISTRARS:
        ping(rir, 5)
