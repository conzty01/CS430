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
def get_2_bits(bytes_lst: list) -> int:
    '''Extract first two bits of a two-byte sequence'''
    return bytes_to_val(bytes_lst) >> 14
# Done
def get_offset(bytes_lst: list) -> int:
    '''Extract size of the offset from a two-byte sequence'''
    return ((bytes_lst[0] & 0x3f) << 8) + bytes_lst[1]
# Done
def findIndexOfDomainName(bytes_lst: list) -> int:
    '''This is just to rename the above function while
        still maintaining the integrity of the tests
        that were provided'''
    return get_offset(bytes_lst)
# Done
def parse_cli_query(filename, q_type, q_domain, q_server=None) -> tuple:
    '''Parse command-line query'''

    if q_server == None:
        q_server = PUBLIC_DNS_SERVER[randint(0,len(PUBLIC_DNS_SERVER)-1)]

    if q_type == "A" or q_type == "AAAA":
        q_type = DNS_TYPES[q_type]
    else:
        raise ValueError("Unknown query type")

    return (q_type,q_domain.split("."),q_server)
# Done
def format_query(q_type: int, q_domain: list) -> bytearray:
    '''Format DNS query'''

    q_domain = [q_domain[0]+"."+q_domain[1]]

    qa = bytearray()
    transID = val_to_2_bytes(randint(0,0xFFFF))                     # [Transaction ID, ]
    flagBytes = val_to_2_bytes(256)                                 # [Flag bytes, ]
    qBytes = val_to_2_bytes(len(q_domain))                          # [# questions, ]
    rrBytes = val_to_n_bytes(0,6)                                   # [RR bytes, , , , , ]

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


    for bList in [transID,flagBytes,qBytes,rrBytes,domBytes]:
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
# Done
def traverse_dom(resp_bytes: bytes, offset: int) -> (str,int):
    domComp1 = resp_bytes[ offset + 1 : offset + resp_bytes[offset] + 1 ].decode()
    offset += resp_bytes[offset] + 1 # Move past domain to length of TLD
    domComp2 = resp_bytes[ offset + 1 : offset + resp_bytes[offset] + 1 ].decode()
    offset += resp_bytes[offset] # Move past TLD

    dom = domComp1 + "." + domComp2

    return (dom,offset)
# Done
def parse_response(resp_bytes: bytes):
    '''Parse server response'''
    # We know the header will be 12 bytes and that the first 2 are the transaction ID,
    #  followed by the flags, # of queries, # of answers, # of authority records, #
    #  of additional records.

    rr_ans = bytes_to_val(resp_bytes[6:8]) # Get the number of answers
    index = 12

    _, index = traverse_dom(resp_bytes,index)

    index += 6 # Move to start of response

    ans = parse_answers(resp_bytes,index,rr_ans)

    return ans
# Done
def parse_answers(resp_bytes: bytes, offset: int, rr_ans: int) -> list:
    '''Parse DNS server answers'''

    ans = []
    for i in range(rr_ans):
        if get_2_bits(resp_bytes[ offset : offset + 2 ]) == 3:                  # first 2 bits are '11'
            domIndex = get_offset(resp_bytes[ offset : offset + 2 ])            # so we have a label pointing to domIndex

            dom, _ = traverse_dom(resp_bytes,domIndex)

        else:   # First 2 bits are not '11' meaning we need to traverse the domain name
            dom, offset = traverse_dom(resp_bytes, offset)

        offset += 2     # Skip to dnsType
        dnsType = bytes_to_val(resp_bytes[ offset : offset + 2 ])
        offset += 4     # Skip past class (Assumed IN for our purposes) to time to list
        ttl = bytes_to_val(resp_bytes[ offset : offset + 4])
        offset += 4     # Move to IP Address length
        ipLen = bytes_to_val(resp_bytes[offset:offset+2])
        offset += 2     # Move to beginning of IP

        if dnsType == DNS_TYPES["A"]:
            addr = parse_address_a(ipLen, resp_bytes[offset:])
        else:
            addr = parse_address_aaaa(ipLen, resp_bytes[offset:])

        offset += ipLen # In case we have mulitple answers
        ans.append((dom,ttl,addr))

    return ans
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

    fin = ""    # Test program requires SPECIFIC output
    for part in retStr[:-1].split(":"):
        fin += hex(int(part,16))[2:] + ":"

    return fin[:-1]
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
