"""Python Web server implementation"""
from socket import socket, AF_INET, SOCK_STREAM
from datetime import datetime

server = socket(AF_INET, SOCK_STREAM)

ADDRESS = "127.0.0.2"  # Local client is going to be 127.0.0.1
PORT = 4300  # Open http://127.0.0.2:4300 in a browser
LOGFILE = "webserver.log"

def writeToLog(time, recFile, ip, browser, log=LOGFILE):
    with open(log,"a") as f:
        output = time+" | "+recFile+" | "+ip+" | "+browser+"\n"
        f.write(output)

def main():
    """Main loop"""
    server.bind((ADDRESS, PORT))
    server.listen(1)

    while True:
        conn, addr = server.accept()
        print("Accepted Connection:- {}".format(addr[0]+":"+str(addr[1])))
        with conn:
            data = conn.recv(1024)
            dataStr = data.decode()
            lines = dataStr.split("\n")

            print("  Parsing Request")

            reqDict = {"Time":str(datetime.now())}

            # Loop-and-a-half
            line1 = lines[0].split()
            if len(line1) == 3:
                method, reqFile, version = line1
            else:
                method, version = line1
                reqFile = None

            reqDict["Method"] = method
            reqDict["ReqFile"] = reqFile
            reqDict["Version"] = version

            for l in lines[1:]:
                sl = l.split(": ")
                if len(sl) == 2:
                    reqDict[sl[0]] = sl[1]

            print("  Parsing Complete")

            print("  Checking Request")
            # Method Not Allowed
            if reqDict["Method"] != "GET":
                print("    Invalid Method:- "+reqDict["Method"])
                conn.send("HTTP/1.1 405 Method Not Allowed\r\n".encode())
                conn.send("<html><head></head><body><h1>405 Method Not Allowed</h1></body></html>".encode())

            # File Not Found
            elif reqDict["ReqFile"] != "/alice30.txt":
                print("    File Not Found:- "+reqDict["ReqFile"])
                conn.send("HTTP/1.1 404 Not Found\r\n".encode())
                conn.send("<html><head></head><body><h1>404 Not Found</h1></body></html>".encode())

            # Fulfill Request
            else:
                print("  Logging Request")
                writeToLog(reqDict["Time"],reqDict["ReqFile"],addr[0],reqDict["User-Agent"])

                print("  Responding")

                print("    Creating Header")
                now = datetime.now()

                header = "HTTP/1.1 200 OK\nContent-Length: 148545\nContent-Type: text/plain; charset=utf-8"
                header += "Date: " + now.strftime("%a %b %d %H:%M:%S %Y") + "\n"
                header += "Last-Modified: Wed Aug 29 11:00:00 2018\n"
                header += "Server: CS430-TCONZ\n"

                print("    Transmitting Header")
                conn.send(header.encode())

                # Transmit File
                print("    Transmitting File")
                with open("alice30.txt","rb") as f:
                    data = f.read(2048)
                    while data:
                        conn.send(data)
                        data = f.read(2048)
                print("    Transmission Complete")

        print("  Closing Connection")
        conn.close()
        print("Connection Closed\n")

if __name__ == "__main__":
    main()
