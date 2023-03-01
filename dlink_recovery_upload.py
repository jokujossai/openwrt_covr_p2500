import argparse
import os
import random
import re
import socket
import struct
import sys
import time

BUFFER_SIZE = 512


TCP_INFO_FMT = None
TCP_INFO_ITEMS = None
if sys.platform in ("linux", "linux2") and os.path.isfile("/usr/include/netinet/tcp.h"):
    with open("/usr/include/netinet/tcp.h", "r") as fh:
        tcp_header = re.sub(
            r"/\*.+?\*/",
            "",
            re.sub(r"\s+", " ", fh.read())
        )
    m = re.search(r"struct tcp_info {(.+?)}", tcp_header)
    if m is not None:
        m.group(1).split(";")
        struct_items = dict(
            (item.strip().split(" ")[1], item.strip().split(" ")[0])
            for item in m.group(1).split(";")
            if item.strip() != ''
        )
        fmt = ""
        for key, value in struct_items.items():
            assert value in ("uint8_t", "uint32_t")
            if value == "uint8_t":
                fmt += "B"
            elif value == "uint32_t":
                fmt += "I"
        TCP_INFO_FMT = fmt
        TCP_INFO_ITEMS = struct_items

if TCP_INFO_FMT is None:
    print("TCP_INFO not supported", file=sys.stderr)
    sys.exit(1)

def wait_ack(s: socket.socket):
    assert TCP_INFO_FMT is not None
    unacked = 1
    while unacked > 0:
        tcp_info_values = struct.unpack(
            TCP_INFO_FMT,
            s.getsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_INFO,
                struct.calcsize(TCP_INFO_FMT)
            )
        )
        tcp_info = dict(
            (key, tcp_info_values[i])
            for i, key in enumerate(TCP_INFO_ITEMS.keys())
        )
        unacked = tcp_info["tcpi_unacked"]


def upload(firmware, host="192.168.0.50", port=80, path="/upgrade.cgi"):
    assert os.path.isfile(firmware)
    fsize = os.stat(firmware).st_size

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.connect((host, port))

    print(f"Connection established to {host}:{port}")

    boundary = "---------------------------"+random.randbytes(6).hex()[:-1]
    content_disposition = 'Content-Disposition: form-data; name="firmware"; filename="firmware.bin"'
    content_type = 'Content-Type: application/octet-stream'
    newline = "\r\n"

    # Calculate HTTP Content-Length
    content_length = (
        2+len(boundary)+len(newline)
        +len(content_disposition)+len(newline)
        +len(content_type)+len(newline)
        +len(newline)
        +fsize+len(newline)
        +2+len(boundary)+2+len(newline)
    )

    # Send HTTP headers
    s.send("""POST {} HTTP/1.1
Host: {}
Content-Length: {}
Content-Type: multipart/form-data; boundary={}
Connection: Keep-Alive

""".format(path, host, content_length, boundary).replace("\n", "\r\n").encode())
    wait_ack(s)

    # Send multipart encapsulation boundary and headers
    s.send("""--{}
{}
{}

""".format(boundary, content_disposition, content_type).replace("\n", "\r\n").encode())
    wait_ack(s)

    # Send firmware
    print("If the upload gets stuck, turn off the device and try again")
    sent_bytes = 0
    with open(firmware, "rb") as fh:
        while True:
            buffer = fh.read(BUFFER_SIZE)
            if buffer == b"":
                break
            s.send(buffer)
            wait_ack(s)
            sent_bytes += len(buffer)
            print("Uploading {}/{}".format(sent_bytes, fsize), end="\r")

    # Send ending boundary
    s.send("""
--{}--
""".format(boundary).replace("\n", "\r\n").encode())
    wait_ack(s)

    print()
    print("Firmware uploaded successfully")

    print(s.recv(4096).decode())

    time.sleep(1)
    s.close()

    percent = 1
    while percent <= 100:
        print(f"Device is upgrading the firmware... {percent}%", end='\r')
        percent += 1
        time.sleep(2.2)
    print("Upgrade should now be successfully finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=str, help="Firmware file to upload")
    parser.add_argument("--host", type=str, default="192.168.0.50", help="Router IP address")
    parser.add_argument("--port", type=int, default=80, help="Router HTTP port")
    parser.add_argument("--path", type=str, default="/upgrade.cgi", help="HTTP path for firmware upgrade")

    args = parser.parse_args()

    upload(args.firmware, args.host, args.port, args.path)
