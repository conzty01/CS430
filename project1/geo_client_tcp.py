'''
GEO TCP Client
'''
#!/usr/bin/env python3

from socket import socket, AF_INET, SOCK_STREAM

HOST = 'localhost'
PORT = 4300


def client():
    '''Main client loop'''
    with socket(AF_INET, SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        data = s.recv(1024)
        serveName = data.decode().split()[-1]
        print('Connected to {}'.format(serveName))

        inStr = input("Enter a country or 'BYE' to quit\n")
        while inStr != "BYE":
            s.sendall(inStr.encode())
            data = s.recv(1024)
            print(data.decode())
            inStr = input("Enter another country to try again or 'BYE' to quit\n")
        s.close()
        print('Connection closed')

def main():
    '''Main function'''
    client()


if __name__ == "__main__":
    main()
