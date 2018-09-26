#!/usr/bin/env python3

import sys
from random import randint, choice, seed
from socket import socket, SOCK_DGRAM, AF_INET


PORT = 53

DNS_TYPES = {
    'A': 1,
    'AAAA': 28,
    'CNAME': 5,
    'MX': 15,
    'NS': 2,
    'PTR': 12,
    'TXT': 16
}

PUBLIC_DNS_SERVER = [
    '1.0.0.1',  # Cloudflare
    '1.1.1.1',  # Cloudflare
    '8.8.4.4',  # Google
    '8.8.8.8',  # Google
    '8.26.56.26',  # Comodo
    '8.20.247.20',  # Comodo
    '9.9.9.9',  # Quad9
    '64.6.64.6',  # Verisign
    '208.67.222.222',  # OpenDNS
    '208.67.220.220'  # OpenDNS
]

# Done
def val_to_2_bytes(value: int) -> list:
    '''Split a value into 2 bytes'''
    #     [left 8 bits, right 8 bits]
    return [value >> 8, value & 0xFF]
# Done
def val_to_n_bytes(value: int, n_bytes: int) -> list:
    '''Split a value into n bytes'''

    retList = []
    while len(retList) < n_bytes:
        #print(bin(value))
        retList = [value & 0xFF] + retList    # Get the last 8 bits and add to the front of the list
        value = value >> 8

    return retList
# Done
def bytes_to_val(bytes_lst: list) -> int:
    '''Merge 2 bytes into a value'''
    return (bytes_lst[0] << 8) + bytes_lst[1]
# Done
def get_2_bits(bytes_lst: list) -> int:
    '''Extract first two bits of a two-byte sequence'''
    return bytes_to_val(bytes_lst) >> 14
# Done
def get_offset(bytes_lst: list) -> int:
    '''Extract size of the offset from a two-byte sequence'''
    return ((bytes_lst[0] & 0x3f) << 8) + bytes_lst[1]
# Done
def parse_cli_query(filename, q_type, q_domain, q_server=None) -> tuple:
    '''Parse command-line query'''

    if q_server == None:
        q_server = PUBLIC_DNS_SERVER[randint(0,len(PUBLIC_DNS_SERVER))]

    q_type = DNS_TYPES[q_type]

    return (q_type,[q_domain],q_server)
# Done
def format_query(q_type: int, q_domain: list) -> bytearray:
    '''Format DNS query'''

    qa = bytearray()
    transID = val_to_2_bytes(randint(0,0xFFFF))                     # [Transaction ID, ]
    flagBytes = val_to_2_bytes(256)                                 # [Flag bytes, ]
    qBytes = val_to_2_bytes(len(q_domain))                          # [# questions, ]
    rrBytes = val_to_n_bytes(1,6)                                   # [RR bytes, , , , , ]

    domBytes = []                                                   # [Dom length, Dom bytes,etc*]
    for dom in q_domain:                                            # The number of domains CAN be more than 1
        for domPart in dom.split("."):
            lenD = val_to_n_bytes(len(domPart),1)
            dEnc = domPart.encode()

            domBytes.extend(val_to_n_bytes(len(domPart),1))         # How long is the domPart
            domBytes.extend(domPart.encode())                       # What is the domPart

        domBytes.extend(val_to_n_bytes(0,1))                        # Buffer at end of domain
        domBytes.extend(val_to_2_bytes(q_type))                     # Type of domain lookup
        domBytes.extend(val_to_2_bytes(1))                          # Class of lookup (default to IN)

    arBytes = val_to_2_bytes(0)
    arBytes.extend([0x29,0x02])
    arBytes.extend(val_to_n_bytes(0,7))

    for bList in [transID,flagBytes,qBytes,rrBytes,domBytes,arBytes]:
        for item in bList:
            qa.append(item)

    return qa
# Done
def send_request(q_message: bytearray, q_server: str) -> bytes:
    '''Contact the server'''
    client_sckt = socket(AF_INET, SOCK_DGRAM)
    client_sckt.sendto(q_message, (q_server, PORT))
    (q_response, _) = client_sckt.recvfrom(2048)
    client_sckt.close()

    return q_response

def parse_response(resp_bytes: bytes):
    '''Parse server response'''
    index = 12 # Prime the index to ignore the DNS header (Maybe not the best idea)
    rr_ans = bytes_to_val(resp_bytes[6:8]) # Get the number of answers

    # print(resp_bytes)
    sansHeader = resp_bytes[index:]

    # print(sansHeader)
    # print(index, resp_bytes[index], resp_bytes[index+1])
    domComp1 = resp_bytes[index:index+resp_bytes[index]+1].decode()
    index += resp_bytes[index] + 1 # Move past domain to length of extension

    # print(index, resp_bytes[index], resp_bytes[index+2])
    domComp2 = resp_bytes[index:index+resp_bytes[index]+1].decode()
    index += resp_bytes[index] + 1 # Move past extension

    # print(index, resp_bytes[index], resp_bytes[index+5])
    index += 5 # Move past buffer and additional RRs

    dom = domComp1 + "." + domComp2

    ans = parse_answers(resp_bytes,index,rr_ans)
    for a in ans:
        a.insert(0,dom)

    return ans

def parse_answers(resp_bytes: bytes, offset: int, rr_ans: int) -> list:
    '''Parse DNS server answers'''
    ans = []

    offset += 2 # Skip past the label
    if rr_ans > 0:
        dnsType = bytes_to_val(resp_bytes[offset:offset+2])
        offset += 4
        ttl = bytes_to_val([bytes_to_val(resp_bytes[offset:offset+2]),bytes_to_val(resp_bytes[offset+2:offset+4])])
        offset += 4
        ipLen = bytes_to_val(resp_bytes[offset:offset+2])

        if dnsType == DNS_TYPES["A"]:
            addr = parse_address_a(ipLen, resp_bytes[offset+2:])
        else:
            addr = parse_address_aaaa(ipLen, resp_bytes[offset+2:])

        return [[ttl,addr]]

    return []
# Done
def parse_address_a(addr_len: int, addr_bytes: bytes) -> str:
    '''Extract IPv4 address'''

    retStr = ""
    for i in range(addr_len):
        retStr += str(addr_bytes[i]) + "."

    return retStr[:-1]
# Done
def parse_address_aaaa(addr_len: int, addr_bytes: bytes) -> str:
    '''Extract IPv6 address'''

    retStr = ""
    for i in range(addr_len):
        b = hex(addr_bytes[i])[2:]
        if len(b) < 2:
            b = "0" + b

        retStr += b

        if i % 2 != 0:
            retStr += ":"

    return retStr[:-1]

    raise NotImplementedError
# Done
def resolve(query: str) -> None:
    '''Resolve the query'''
    q_type, q_domain, q_server = parse_cli_query(*query[0])
    query_bytes = format_query(q_type, q_domain)
    response_bytes = send_request(query_bytes, q_server)
    answers = parse_response(response_bytes)
    print('DNS server used: {}'.format(q_server))
    for a in answers:
        print('Domain: {}'.format(a[0]))
        print('TTL: {}'.format(a[1]))
        print('Address: {}'.format(a[2]))

def main(*query):
    '''Main function'''
    if len(query[0]) < 3 or len(query[0]) > 4:
        print('Proper use: python3 resolver.py <type> <domain> <server>')
        exit()
    resolve(query)


if __name__ == '__main__':
    main(sys.argv)
