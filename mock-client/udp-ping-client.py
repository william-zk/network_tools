#!/usr/bin/env python

from __future__ import print_function

import socket
import sys
import time
import string
import random
import signal
import sys
import os
import logging
import struct

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(filename='client.log', level=logging.DEBUG, format=LOG_FORMAT)

INTERVAL = 1000  #unit ms
LEN =64
IP=""
PORT=0
BURST = 1

count=0
count_of_received=0
rtt_sum=0.0
rtt_min=99999999.0
rtt_max=0.0

def int2byte8(x):
    return chr((x >> 56) & 0xFF) + chr((x >> 48) & 0xFF) + chr((x >> 40) & 0xFF) + chr(x >> 32 & 0xFF) + chr((x >> 24) & 0xFF) + chr((x >> 16) & 0xFF) + chr((x >> 8) & 0xFF) + chr(x & 0xFF)

def byte82int(str):
    arr = struct.unpack('>BBBBBBBB', str)
    res = (arr[0] << 56) | (arr[1] << 48) |(arr[2] << 40) | (arr[3] << 32) | (arr[4] << 24) | (arr[5] << 16) |(arr[6] << 8) | arr[7]
    return res

def get_curr_time_ms():
    return int(time.time() * 1000)


def signal_handler(signal, frame):
    if count!=0 and count_of_received!=0:
        print('')
        print('--- ping statistics ---')
    if count!=0:
        print('%d packets transmitted, %d received, %.2f%% packet loss'%(count,count_of_received, (count-count_of_received)*100.0/count))
    if count_of_received!=0:
        print('rtt min/avg/max = %.2f/%.2f/%.2f ms'%(rtt_min,rtt_sum/count_of_received,rtt_max))
    os._exit(0)

def random_string(length):
        return ''.join(random.choice(string.ascii_letters+ string.digits ) for m in range(length))

def gen_packet(seq, timestamp, length):
    seq_b = int2byte8(seq)
    timestamp_b = int2byte8(timestamp)
    payload_len = length - len(seq_b) - len(timestamp_b)
    payload = random_string(payload_len)
    packet = seq_b + timestamp_b + payload.encode()
    return packet


if len(sys.argv) != 3 and len(sys.argv)!=4 :
    print(""" usage:""")
    print("""   this_program <dest_ip> <dest_port>""")
    print("""   this_program <dest_ip> <dest_port> "<options>" """)

    print()
    print(""" options:""")
    print("""   LEN         the length of payload, unit:byte""")
    print("""   INTERVAL    the seconds waited between sending each packet, as well as the timeout for reply packet, unit: ms""")

    print()
    print(" examples:")
    print("   ./udpping.py 44.55.66.77 4000")
    print('   ./udpping.py 44.55.66.77 4000 "LEN=400;INTERVAL=2000;BURST=1"')
    print("   ./udpping.py fe80::5400:ff:aabb:ccdd 4000")
    print()

    exit()

IP=sys.argv[1]
PORT=int(sys.argv[2])

is_ipv6=0

if IP.find(":")!=-1:
    is_ipv6=1

if len(sys.argv)==4:
    exec(sys.argv[3])

if LEN<5:
    print("LEN must be >=5")
    exit()
if INTERVAL<50:
    print("INTERVAL must be >=50")
    exit()
if BURST <= 0:
    print("INTERVAL must be > 0")
    exit()

signal.signal(signal.SIGINT, signal_handler)

if not is_ipv6:
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
else:
    sock = socket.socket(socket.AF_INET6,socket.SOCK_DGRAM)

print("UDPping %s via port %d with %d bytes of payload"% (IP,PORT,LEN))
sys.stdout.flush()

while True:
    for i in range(0, BURST):
        count += 1
        timestamp = get_curr_time_ms()
        packet = gen_packet(count, timestamp, LEN)
        print("Send to %s:%s, seq=%d" % (IP, PORT, count))
        logging.debug("Send to %s:%s, seq=%d" % (IP, PORT, count))
        sock.sendto(packet, (IP, PORT))

    deadline = get_curr_time_ms() + INTERVAL
    recv_num = 0
    while True:
        received = 0
        rtt = 0.0
        timeout = float((deadline - get_curr_time_ms()))/1000.0
        if timeout < 0:
            break
        #print "timeout=",timeout
        sock.settimeout(timeout)
        try:
            recv_data,addr = sock.recvfrom(65536)
            if len(recv_data) == LEN and addr[0]==IP and addr[1]==PORT:
                recv_seq = byte82int(recv_data[0:8])
                rtt =  get_curr_time_ms() - byte82int(recv_data[8:16])
                logging.debug("Reply from %s, seq=%d, time=%.2fms" % (IP, recv_seq, rtt))
                print("Reply from %s, seq=%d, time=%.2fms" % (IP, recv_seq, rtt))
                sys.stdout.flush()
                received = 1
                recv_num = recv_num + 1
        except socket.timeout:
            print("Request timed out, recv num is: %d" % recv_num)
            logging.debug("Request timed out, recv num is: %d" % recv_num)
            break
        except :
            print("unkonw err, recv num is: %d" % recv_num)
            logging.debug("unkonw err, recv num is: %d" % recv_num)
            pass

        if received == 1:
            count_of_received += 1
            rtt_sum += rtt
            rtt_max = max(rtt_max,rtt)
            rtt_min = min(rtt_min,rtt)
        else:
            print("Request timed out")
            logging.debug("Request timed out")
            sys.stdout.flush()

        if (recv_num < BURST):
            time_remaining = deadline - get_curr_time_ms()
            if (time_remaining > 0):
                continue
            else:
                print("Request timed out, recv num is: %d" % recv_num)
                logging.debug("Request timed out, recv num is: %d" % recv_num)
                recv_num = 0
                break
        else:
            time_remaining = deadline - get_curr_time_ms()
            if (time_remaining > 0):
                time.sleep(time_remaining / 1000)
                recv_num = 0
                break
