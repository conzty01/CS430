<<<<<<< HEAD
# Custom dig

Complete the following programming project and push code to your GitHub repository.

**Process records of type A (IPv4) or AAAA (IPv6) only. If a server returns CNAME record instead, ignore it.**

Use *yahoo.com* as an example of a clean and simple response.

Read record type (**A** or **AAAA**), domain name, and an optional DNS server as parameters passed to your program.

```
python3 resolver.py A luther.edu 1.1.1.1
```
or
```
python3 resolver.py AAAA yahoo.com
```

1. Format a DNS request using the following values:

    * Transaction ID: auto-incremental or random
    * Flags: standard query (recursion bit set to 1, other bits are 0)
    * Questions: 1
    * Answer RRs: 0
    * Authority RRs: 0
    * Additional RRs: 0
    * Name: user-provided
    * Type: user-provided
    * Class: IN (0x0001)

2. If the DNS address is not specified, pick one of the well-known public servers.

3. Create a UDP socket connection and send the request to the DNS server.

4. Parse the response message from the DNS server to extract all addresses (there could be more than 1).

5. Print the address of the DNS server used.

6. Display the received information in the following format:

```
Name: <domain name>
TTL: record time-to-live
Addresses: <list of addresses received>
```

7. Pass all tests provided.

```
python3 -m pytest test_resolver.py
```

## Approach

* Look at a valid DNS request (eg. ping www.luther.edu and capture the traffic)

![DNS request](dns_query.png)

* Analyze the structure of a message (see the links below for details) and replicate it

![DNS request](dns_query_hex.png)

* Format your own message, byte by byte (you may want to use Python's bytearray for that)

* Make your client format a message based on user input (domain, record type)

* Send the message and receive the response

* Parse the response and present the result (IP address). Consider simple cases (domain - one or more address(es)), ignore complex paypal-like resolutions with multiple pseudos.

## Functions

> 'Begin at the beginning,' the King said gravely, 'and go on till you come to the end: then stop.'

### `val_to_2_bytes(value: int) -> list`

`val_to_2_bytes` takes an integer and returns that number converted to a list of 2 bytes (numbers between 0 and 255). Use shift (>>) and binary and (&) to extract left and right 8 bits. This function is used extensively as many fields in the DNS request and response are using 2 bytes, even if a value fits 1 byte.

```
43043 = 0b1010100000100011 => [0b10101000, 0b00100011] = [168, 35]
                                 left 8      right 8
```

### `val_to_n_bytes(value: int, n_bytes: int) -> list`

`val_to_n_bytes` takes an integer and the target list size, converting the number to a list of the specified size. Use shifting (<<, >>) and bit masking (&) in a loop to generate the list. You don't have to use this function but it's a great way to learn bitwise operations.

```
430430 = 0b1101001000101011110 => [0b00000110, 0b10010001, 0b01011110] = [6, 145, 94]
                                     left 8      middle 8    right 8
```

### `bytes_to_val(bytes_lst: list) -> int`

`bytes_to_val` takes a list of bytes and returns their value as a single integer. Use shift (<<) and addition in a loop to construct the result. This function is used extensively as many DNS fields are stored in 2 bytes.

```
[6, 145, 94] = [0b110, 0b10010001, 0b01011110] => 0b1101001000101011110 = 430430
```

### `get_2_bits(bytes_lst: list) -> int`

`get_2_bits` extracts the leftmost 2 bits from a 2-byte sequence. Use a simple shift to extract the target bits. This function is used to determine whether the domain is stored in the answer as a label or a pointer. See the provided references for details on those two formats.

```
0xc00c = 0b1100000000001100 => leftmost 2 bits are 0b11 = 3
```

### `get_offset(bytes_lst: list) -> int`

`get_offset` extracts the rightmost 14 bits from a 2-byte sequence. This function can be used to extract the location of the domain name inside a response. Note that a response may contain either labels or pointers, so don't rely on the *magic* of `0xc00c`. A more descriptive name for this function is *get_domain_name_location_within_a_server_response*. Do not confuse the offset found by this function with the offset of answers within the response.

```
0xc00c = 0b1100000000001100 => rightmost 14 bits are 0b1100= 12
```

### `parse_cli_query(filename, q_type, q_domain, q_server=None) -> tuple`

`parse_cli_query` takes a filename, a query type, the domain name to resolve, and an optional server address as parameters and returns a tuple of the numeric value of the query type (as found in the `DNS_TYPES` dictionary), domain name (as a list of strings), and the server address. If the server address is not specified, pick one randomly as follows: `choice(PUBLIC_DNS_SERVER)`.

### `format_query(q_type: int, q_domain: list) -> bytearray`

`format_query` takes the query type and the domain name as parameters and builds a query as a bytearray. Bytearrays are mutable byte sequences in Python, so you should start with an empty one and use `append` or `extend` to form a valid DNS query. Transaction id should be chosen at random as follows: `randint(0, 65535)`. Use default value, `0x100` for the flags. The domain name should be in the **QNAME** format, terminated by `\0`.

```
56 f0 01 00 00 01 00 00 00 00 00 00 06 6c 75 74 68 65 72 03 65 64 75 00 00 01 00 01
|---| |---| |---| |---| |---| |---| |------------------| |---------| || |---| |---| 
|id | |flags, # of questions etc  | | luther           | | edu     | \0 |typ| |cls|
```

### `send_request(q_message: bytearray, q_server: str) -> bytes`

`send_request` takes the formatted message and the server address and sends the DNS request. This function returns the DNS response for the parser to process. Implemented for your convenience.

### `parse_response(resp_bytes: bytes)`

`parse_response` takes bytes received from the server and returns a list (*or a tuple*, it doesn't matter) where each item is a tuple of the domain name, TTL, and the address, as extracted from the server response. This function processes the response header (first 12 bytes and the query), calls `parse_answers` to parse the specific answer(s), and returns the results returned by `parse_answers`. You don't need to validate values in the response (i.e. transaction id and flags) but you have to extract the number of answers from the header and the starting byte of the answers.

### `parse_answers(resp_bytes: bytes, offset: int, rr_ans: int) -> list`

`parse_answers` takes the response message bytes, starting position for the answer(s) within the response, and the number of answers. It returns a list of tuples (domain, ttl, address). Do not confuse the *offset* in this function (a better(?) name would be *number_of_bytes_from_the_beginning_of_the_response_to_the_first_answer*) and the *domain_name_start_offset*. Keep in mind that the domain name may be in different format, *label* or *pointer*. You should be able to process both.

Once you've processed an answer, add the results to the list and move to the next one, if present. Once all the answers are collected, return the list of tuples.

```
c0 0c 00 01 00 01 00 00 00 05 00 04 ae 81 19 aa
|---| |---| |---| |---------| |---| |---------|
|ptr| |typ| |cls| | ttl     | |len| | address |
```

### `parse_address_a(addr_len: int, addr_bytes: bytes) -> str`

`parse_address_a` extracts IPv4 address from the response and returns it in the dotted-decimal notation.

### `parse_address_aaaa(addr_len: int, addr_bytes: bytes) -> str`

`parse_address_aaaa` extracts IPv6 address from the response and returns it in the hex-colon notation.

### `resolve(query: str) -> None`

`resolve` calls and other functions and prints the results. It is implemented for your convenience.

## Resources

* [RFC 1035 - Domain names - implementation and specification](https://tools.ietf.org/html/rfc1035)

* [The TCP/IP Guide - DNS Messaging and Message, Resource Record and Master File Formats](http://www.tcpipguide.com/free/t_DNSMessagingandMessageResourceRecordandMasterFileF.htm)

* [Chapter 15 DNS Messages](http://www.zytrax.com/books/dns/ch15/)

* [Domain Name System (DNS) Parameters](http://www.iana.org/assignments/dns-parameters/dns-parameters.xhtml)

* [Python Bytes, Bytearray - w3resource](https://www.w3resource.com/python/python-bytes.php)
=======
# Router

## Task

In this project you will be writing a set of procedures to implement a distributed asynchronous distance-vector routing protocol. Eventually we'll try to make all the routers work together in the lab environment. In order to achieve general compatibility, it's mandatory that you use **Ubuntu 18.04** as a platform and **Python 3.6** as the implementation language.

I recommend you implement your router application in stages, from a basic socket application to a full-fledged router.

This is going to be a challenging project, not only in the sense of correctly implementing the distance-vector routing algorithm but also because your program must handle multiple connections that will operate asynchronously. There are several approaches to correctly deal with a bunch of asynchronous sockets, we are going to use the Python `select` method. The `select` method takes three lists, (sockets I want to **read from**, sockets I want to **write to**, sockets that might have **errors**) and checks all of the sockets lists. When the function returns (either right away, or after a set time), the lists you passed in will have been transformed into lists of sockets that you may want to read, write or check for errors respectively. You can be assured that when you make a read or write call, the call will not block.

I would strongly suggest that you take the time to write yourself a high-level design for this project before you start writing code. You may also find it useful to write a little server program that keeps multiple connections active and adds messages to a queue. Doing something very simple like this is a good way to learn and check out the problems you are likely to run into with asynchronous communications before you get mired in the whole distance-vector routing.

Each router should maintain a set of NEIGHBORS (adjacent routers) and a ROUTING_TABLE as a dictionary in the following format:

```
destination: [cost, next_hop]
```

## Stage 1: Read the Configuration File

We start with a simple application that reads a router's configuration from a text file, displays its status (neighbors and cost of getting to them), and starts listening for incoming UDP connections on port 4300. The configuration contains names of your directly connected neighbors and the cost to reach those neighbors.

You should write 4 identical files, each one for a different address (127.0.0.**x**) and port (4300**x**). By the end of the project you should be able to test your routers locally, at the very least.

### Configuration file format

```
Router_1_IP_address
Neighbor_1_IP_addres Cost_of_getting_to_neighbor_1
Neighbor_2_IP_addres Cost_of_getting_to_neighbor_2

Router_2_IP_address
Neighbor_1_IP_addres Cost_of_getting_to_neighbor_1
Neighbor_2_IP_addres Cost_of_getting_to_neighbor_2
Neighbor_3_IP_addres Cost_of_getting_to_neighbor_3
```

File *network_simple.txt* represents the following network:

![Simple network](final_project/network_simple.png)

network_simple.txt
```
127.0.0.1
127.0.0.2 1
127.0.0.3 3
127.0.0.4 7

127.0.0.2
127.0.0.1 1
127.0.0.3 1

127.0.0.3
127.0.0.1 3
127.0.0.2 1
127.0.0.4 2

127.0.0.4
127.0.0.1 7
127.0.0.3 2
```

*TOML* file provides some explanation. **You don't have to read network configuration from TOML config file**.

## Stage 1: Welcome to the Party

Start with a socket application that reads network configuration from a file, binds to port 4300, and prints the routing table.

### Stage 1 Functionality

1. Read the configuration file
2. Pick an appropriate address
3. Display the chosen router's neighborhood (names and costs)
4. Start listening on **UDP** port 4300

## Stage 2: Close Encounters of the Third Kind

1. Your program must connect to the IP addresses specified in the configuration file. Your client should accept a path to the configuration file as a command line argument so that we can try out a couple of different configurations. Note that in order to bootstrap the network you are going to need to have your program retry connections that fail.

2. Your program must also accept incoming IP connections from neighbors which may inform you of a link cost change, or may ask you to deliver a message to a particular IP address.

3. Our protocol will use 3 (three) types of messages: **UPDATE (0)**, **HELLO (1)**, and **STATUS (2)**. The implementation of the first two is required, **STATUS** is optional. You should use `bytearray` or `struct` to format and parse messages.

### UPDATE message format

* The first byte of the message (0): 0

* Next four bytes (1-4): IP address

* The next byte (5): cost

* The same pattern (IP address followed by cost) repeats. 

### HELLO message format

* The first byte of the message (0): 1

* Next four bytes (1-4): source IP address

* Next four bytes (5-8): destination IP address

* The rest of the message (9+): text (characters)

### STATUS message format

* The first byte of the message (0): 2

### Event loop

1. Do we have pending connections?

    1. Accept new connections

    2. Add to the listener list

    3. Add IP addresses to the neighbor list

2. Process incoming messages

    1. If UPDATE, then update the routing table
        * Does my vector change?  If so, then set flag to `update_vector`
        * Print the updated routing table

    2. If DELIVERY, then forward to the destination

    3. If STATUS, then respond with the routing table

3. Is `update_vector` flag set?

    1. Send the new vector to all neighbors that can accept data

4. Check my neighbor list against the list of currently connected neighbors

    1. If missing neighbors, then try to initiate connections to them

    2. If successful, then add the new neighbor to list

    3. Send the new neighbor my distance vector

### Stage 2 Functionality

1. Read the configuration file name as a command line parameter
2. Read the neighborhood information from the configuration file
3. Send a router's table to all neighbors
4. Receive updates from the neighbors
5. Keep listening and be ready to update the routing table

## Stage 3: Routing

Write the following routing functions.

* Read a configuration file for your specific router and add each neighbor to a set of neighbors.

* Build an initial routing table as a dictionary with nodes as keys. Dictionary values should be a distance to the node and the next hop address. Initially, the dictionary must contain your neighbors only.

```python
{'destination':[cost, 'next_hop']}
```

* Format the update message based on the values in the routing table and return the message. For example, a message advertising routes to **127.0.0.1** of cost **10** and to **127.0.0.2** of cost **5** is the following `bytearray`:

```
0x0 0x7f 0x0 0x0 0x1 0xA 0x7f 0x0 0x0 0x2 0x5
```

* Parse the update message and return `True` if the table has been updated. The function must take a message (raw bytes) and the neighbor's address and update the routing table, if necessary.

* Print current routing table. The function must print the current routing table in a human-readable format (rows, columns, spacing).

* Parse a message to deliver. The function must parse the message and extract the destination address. Look up the destination address in the routing table and return the next hop address.

* Router works with properly implemented routers of other students.

## Functions

### read_file(filename)

* Read a configuration file for your specific router and add each neighbor to a set of neighbors.
* Build an initial routing table as a dictionary with nodes as keys.
* Dictionary values should be a distance to the node and the next hop address (ie. {'destination':[cost, 'next_hop']}).
* Initially, the dictionary must contain your neighbors only.

### format_update_msg()

* Format the update message based on the values in the routing table.
* The message advertising routes to 127.0.0.1 of cost 10 and to 127.0.0.2 of cost 5 is a bytearray in the following format
```
0x0 0x7f 0x0 0x0 0x1 0xA 0x7f 0x0 0x0 0x2 0x5
```
* The function must return the message.

### update_table(msg, neigh_addr)

* Parse the update message.
* The function must take a message (raw bytes) and the neighbor's address and update the routing table, if necessary.
* The function must return True if the table has been updated.

### print_status()

* Print current routing table.
* The function must print the current routing table in a human-readable format (rows, columns, spacing).

### deliver_msg()

* Parse a message to deliver.
* The function must parse the message and extract the destination address.
* Look up the destination address in the routing table and return the next hop address.

### send_update(node)

* Send updated routing table to the specified node (router)

## Running the simulation

Start each router as follows:

```
python3 router_1.py network_simple.txt
python3 router_1.py network_simple.txt
python3 router_1.py network_simple.txt
python3 router_1.py network_simple.txt
```

![Simulation](final_project/router.apng)

## References

* [socket — Low-level networking interface — Python 3.7.1 documentation](https://docs.python.org/3/library/socket.html)
* [select — Waiting for I/O completion — Python 3.7.1 documentation](https://docs.python.org/3/library/select.html)

* [toml-lang/toml: Tom's Obvious, Minimal Language](https://github.com/toml-lang/toml)
>>>>>>> refs/remotes/origin/master
