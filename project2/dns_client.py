#!/usr/bin/env python3
#encoding: UTF-8

import sys
import socket


class DNSClient:
    '''DNS Client class'''
    def __init__(self,dnsIP='1.1.1.1'):
        self.dnsPort = 53
        self.dnsIP = dnsIP
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # SOCK_DGRAM specifies UDP

    def sendReq(self,lookupURL,type='A'):
        pass

    def getResP(self):
        pass

def main(argv):
    
    print('Project 2')
    dnsClient = DNSClient()


if __name__ == '__main__':
    main(sys.argv)
