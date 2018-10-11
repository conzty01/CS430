'''
DNS Name Server
'''
#!/usr/bin/env python3

import sys
from random import randint, choice
from socket import socket, SOCK_DGRAM, AF_INET


HOST = "localhost"
PORT = 43053

DNS_TYPES = {
    1: 'A',
    2: 'NS',
    5: 'CNAME',
    12: 'PTR',
    15: 'MX',
    16: 'TXT',
    28: 'AAAA'
}

TTL_SEC = {
    '1s': 1,
    '1m': 60,
    '1h': 60*60,
    '1d': 60*60*24,
    '1w': 60*60*24*7,
    '1y': 60*60*24*365
    }

# Done
def val_to_bytes(value: int, n_bytes: int) -> list:
    '''Split a value into n bytes'''

    retList = []
    while len(retList) < n_bytes:
        retList = [value & 0xFF] + retList    # Get the last 8 bits and add to the front of the list
        value = value >> 8

    return retList

# Done
def bytes_to_val(bytes_lst: list) -> int:
    '''Merge 2 bytes into a value'''
    res = 0
    for num,pos in enumerate(range(len(bytes_lst),0,-1)):
        res += bytes_lst[pos-1] << (8*num)

    return res

# Done
def get_left_bits(bytes_lst: list, n_bits: int) -> int:
    '''Extract left n bits of a two-byte sequence'''
    num = bytes_to_val(bytes_lst)
    return num >> (len(bin(num)[2:])-n_bits)

# Done
def get_right_bits(bytes_lst: list, n_bits) -> int:
    '''Extract right n bits of a two-byte sequence'''
    num = bytes_to_val(bytes_lst)
    byteStr = ""
    for i in range(n_bits):
        byteStr += "1"
    return num & bytes_to_val([int(bytes(byteStr,"utf8"),2)])

# Done
def read_zone_file(filename: str) -> tuple:
    '''Read the zone file and build a dictionary'''
    zone = dict()
    with open(filename) as zone_file:
        origin = zone_file.readline().split()[1].rstrip('.')
        defaultTTL = zone_file.readline().split()[1]

        line = zone_file.readline()
        dom = ""
        while line != "":
            sl = line.split()
            if "1" not in sl[0]:        # Either new domain or old domain and no ttl
                if "I" not in sl[0]:    # New domain name
                    dom = sl[0]         # Reassign dom
                    zone[dom] = []      # Set dom in dict
                    if "1" in sl[1]:    # All items are present
                        ttl = sl[1]     # Assign all items
                        c = sl[2]
                        ty = sl[3]
                        addr = sl[4]
                    else:               # ttl not present
                        ttl = defaultTTL
                        c = sl[1]       # Assign all other items
                        ty = sl[2]
                        addr = sl[3]
                else:                   # Old domain and no ttl
                    ttl = defaultTTL
                    c = sl[0]
                    ty = sl[1]
                    addr = sl[2]
            else:                       # Old domain and we have a ttl
                ttl = sl[0]
                c = sl[1]
                ty = sl[2]
                addr = sl[3]

            zone[dom].append((ttl,c,ty,addr))
            line = zone_file.readline()

    return (origin, zone)

# Done
def traverse_dom(resp_bytes: bytes, offset: int) -> (str,int):
    dom = ""
    while bytes_to_val(resp_bytes[offset:offset+1]) != 0:
        domComp = resp_bytes[ offset + 1 : offset + resp_bytes[offset] + 1 ].decode()
        offset += resp_bytes[offset] + 1
        dom += domComp + "."

    dom = dom.rstrip(".")

    return (dom,offset)

# Done
def parse_request(origin: str, msg_req: bytes) -> tuple:
    '''Parse the request'''
    transID = bytes_to_val(msg_req[:2])                         # Increment the Transaction ID
    index = 12                                                  # Skip to the query
    q = msg_req[12:]                                            # Query is the entire message sans header
    fullDom, index = traverse_dom(msg_req, index)

    if fullDom[fullDom.index(".")+1:] != origin:
        raise ValueError("Unknown zone")

    queryDom = fullDom.split(".")[0]

    if bytes_to_val(msg_req[-4:-2]) not in (1,28):
        raise ValueError("Unknown query type")
    else:
        q_type = bytes_to_val(q[-4:-2])                         # Get the DNS type
        index += 2

    if bytes_to_val(msg_req[-2:]) != 1:
        raise ValueError("Unknown class")

    return (transID,queryDom,q_type,q)

# Done
def format_response(zone: dict, trans_id: int, qry_name: str, qry_type: int, qry: bytearray) -> bytearray:
    '''Format the response'''

    zoneInfo = zone[qry_name]                           # Get the zone information
    ans = []
    for i in zoneInfo:
        if i[2] == DNS_TYPES[qry_type]:                 # If an entry is of the same DNS type
            ans.append(i)                               # Add it to the answers

    resp = bytearray()
    resp.extend(val_to_bytes(trans_id,2))               # Add Transaction ID
    resp.extend([0x81,0x00])                            # Add Flags
    resp.extend(val_to_bytes(1,2))                      # Add number of questions
    resp.extend(val_to_bytes(len(ans),2))               # Add number of answers
    resp.extend(val_to_bytes(0,4))                      # Add number of additional/authority records
    resp += qry                                         # Add the query

    for aTup in ans:
        resp.extend([0xc0,0x0c])                        # Add label for domain name
        resp.extend(val_to_bytes(qry_type,2))           # Add query type
        resp.extend(val_to_bytes(1,2))                  # Add query class
        resp.extend(val_to_bytes(TTL_SEC[aTup[0]],4))   # Add time to live

        if qry_type == 1:                               # If type 'A'
            addrPts = aTup[3].split(".")
            resp.extend(val_to_bytes(len(addrPts),2))   # Add length of address
            for pt in addrPts:
                resp.append(int(pt))                    # Add part of address

        else:                                           # If type 'AAAA'
            addrPts = aTup[3].split(":")
            resp.extend(val_to_bytes(len(addrPts)*2,2)) # Add length of address (each part is made up of 2 bytes)
            for pt in addrPts:
                resp.extend(val_to_bytes(int(pt,16),2)) # Add part of address

    return resp

# Done
def run(filename: str) -> None:
    '''Main server loop'''
    server_sckt = socket(AF_INET, SOCK_DGRAM)
    server_sckt.bind((HOST, PORT))
    origin, zone = read_zone_file(filename)
    print("Listening on %s:%d" % (HOST, PORT))

    while True:
        (request_msg, client_addr) = server_sckt.recvfrom(512)
        try:
            trans_id, domain, qry_type, qry = parse_request(origin, request_msg)
            msg_resp = format_response(zone, trans_id, domain, qry_type, qry)
            server_sckt.sendto(msg_resp, client_addr)
        except ValueError as ve:
            print('Ignoring the request: {}'.format(ve))
        except KeyError as ke:
            print('Ignoring the request: {} not in zone.'.format(ke))
    server_sckt.close()

# Done
def main(*argv):
    '''Main function'''
    if len(argv[0]) != 2:
        print('Proper use: python3 nameserver.py <zone_file>')
        exit()
    run(argv[0][1])


if __name__ == '__main__':
    main(sys.argv)
