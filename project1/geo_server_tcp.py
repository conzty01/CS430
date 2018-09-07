'''
GEO TCP Server
'''
#!/usr/bin/env python3

from socket import socket, AF_INET, SOCK_STREAM

FILE_NAME = 'geo_world.txt'
HOST = 'localhost'
PORT = 4300


def read_file(filename: str): # -> dict:
    '''Read world territories and their capitals from the provided file'''
    world = dict()
    with open(filename,"r") as f:
        for line in f:
            sl = line.split("-")
            world[sl[0].rstrip()] = sl[-1].lstrip()
    return world


def server(worldDict: dict): # -> None:
    '''Main server loop'''

    with socket(AF_INET, SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)
        print('Listening on {}:{}'.format(HOST,PORT))
        conn, addr = s.accept()

        with conn:
            print('Accepted connection from {}'.format(addr[0]))
            conn.sendall("Hi, I'm GEO101".encode())

            while True:
                data = conn.recv(1024)
                dataStr = data.decode()

                print("User Query:".format(dataStr))

                if dataStr in worldDict.keys():
                    conn.sendall(worldDict[dataStr].encode())
                else:
                    conn.sendall("There is no such country".encode())

        print('Disconnected {}'.format(addr))


def main():
    '''Main function'''
    world = read_file(FILE_NAME)
    server(world)


if __name__ == "__main__":
    main()
