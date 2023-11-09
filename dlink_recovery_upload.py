#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
#   D-Link COVR-P2500 flash utility
#
#   Upload firmware to the device with waiting for ACK after each TCP packet.
#
#   Copyright (C) 2023 Daniel Linjama <daniel@dev.linjama.com>
#
#   Permission is hereby granted, free of charge, to any person obtaining a copy of
#   this software and associated documentation files (the “Software”), to deal in the
#   Software without restriction, including without limitation the rights to use, copy,
#   modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
#   and to permit persons to whom the Software is furnished to do so, subject to the
#   following conditions:
#
#   The above copyright notice and this permission notice shall be included in all
#   copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#   INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#   PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#   HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#   OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#   SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import argparse
import ctypes
import ctypes.wintypes
import os
import random
import socket
import sys
import time

BUFFER_SIZE = 512
ACK_TIMEOUT = 10


if sys.platform in ("linux", "linux2"):
    class TCP_INFO(ctypes.Structure):
        """
        tcp_info structure (https://sourceware.org/git?p=glibc.git;a=blob_plain;f=sysdeps/gnu/netinet/tcp.h;hb=HEAD)

        struct tcp_info
        {
            uint8_t     tcpi_state;
            uint8_t     tcpi_ca_state;
            uint8_t     tcpi_retransmits;
            uint8_t     tcpi_probes;
            uint8_t     tcpi_backoff;
            uint8_t     tcpi_options;
            uint8_t     tcpi_snd_wscale : 4, tcpi_rcv_wscale : 4;

            uint32_t    tcpi_rto;
            uint32_t    tcpi_ato;
            uint32_t    tcpi_snd_mss;
            uint32_t    tcpi_rcv_mss;

            uint32_t    tcpi_unacked;
            uint32_t    tcpi_sacked;
            uint32_t    tcpi_lost;
            uint32_t    tcpi_retrans;
            uint32_t    tcpi_fackets;

            /* Times. */
            uint32_t    tcpi_last_data_sent;
            uint32_t    tcpi_last_ack_sent;	/* Not remembered, sorry.  */
            uint32_t    tcpi_last_data_recv;
            uint32_t    tcpi_last_ack_recv;

            /* Metrics. */
            uint32_t    tcpi_pmtu;
            uint32_t    tcpi_rcv_ssthresh;
            uint32_t    tcpi_rtt;
            uint32_t    tcpi_rttvar;
            uint32_t    tcpi_snd_ssthresh;
            uint32_t    tcpi_snd_cwnd;
            uint32_t    tcpi_advmss;
            uint32_t    tcpi_reordering;

            uint32_t    tcpi_rcv_rtt;
            uint32_t    tcpi_rcv_space;

            uint32_t    tcpi_total_retrans;
        };
        """
        _fields_ = [
            ("tcpi_state", ctypes.c_uint8),
            ("tcpi_ca_state", ctypes.c_uint8),
            ("tcpi_retransmits", ctypes.c_uint8),
            ("tcpi_probes", ctypes.c_uint8),
            ("tcpi_backoff", ctypes.c_uint8),
            ("tcpi_options", ctypes.c_uint8),
            ("tcpi_snd_wscale", ctypes.c_uint8, 4),
            ("tcpi_rcv_wscale", ctypes.c_uint8, 4),

            ("tcpi_rto", ctypes.c_uint32),
            ("tcpi_ato", ctypes.c_uint32),
            ("tcpi_snd_mss", ctypes.c_uint32),
            ("tcpi_rcv_mss", ctypes.c_uint32),

            ("tcpi_unacked", ctypes.c_uint32),
            ("tcpi_sacked", ctypes.c_uint32),
            ("tcpi_lost", ctypes.c_uint32),
            ("tcpi_retrans", ctypes.c_uint32),
            ("tcpi_fackets", ctypes.c_uint32),

            ("tcpi_last_data_sent", ctypes.c_uint32),
            ("tcpi_last_ack_sent", ctypes.c_uint32),
            ("tcpi_last_data_recv", ctypes.c_uint32),
            ("tcpi_last_ack_recv", ctypes.c_uint32),

            ("tcpi_pmtu", ctypes.c_uint32),
            ("tcpi_rcv_ssthresh", ctypes.c_uint32),
            ("tcpi_rtt", ctypes.c_uint32),
            ("tcpi_rttvar", ctypes.c_uint32),
            ("tcpi_snd_ssthresh", ctypes.c_uint32),
            ("tcpi_snd_cwnd", ctypes.c_uint32),
            ("tcpi_advmss", ctypes.c_uint32),
            ("tcpi_reordering", ctypes.c_uint32),

            ("tcpi_rcv_rtt", ctypes.c_uint32),
            ("tcpi_rcv_space", ctypes.c_uint32),

            ("tcpi_total_retrans", ctypes.c_uint32),
        ]

    def wait_ack(s: socket.socket):
        """
        Linux compatible wait_ack implementation.

        Waits until tcp_info.tcpi_unacked is zero.

        :param socket.socket s: The socket to check for unacked TCP packets
        :raises RuntimeError: if ACK_TIMEOUT exceeded
        """
        timeout = time.time() + ACK_TIMEOUT
        unacked = 1
        while unacked > 0:
            # Check timeout
            if time.time() > timeout:
                raise RuntimeError("ACK timeout")

            # Fetch tcp_info
            tcp_info = TCP_INFO.from_buffer_copy(
                s.getsockopt(
                    socket.IPPROTO_TCP,
                    socket.TCP_INFO,
                    ctypes.sizeof(TCP_INFO)
                )
            )

            unacked = tcp_info.tcpi_unacked
elif sys.platform == "win32":
    class TCP_INFO_v0(ctypes.Structure):
        """
        TCP_INFO_v0 structure (https://learn.microsoft.com/en-us/windows/desktop/api/mstcpip/ns-mstcpip-tcp_info_v0)

        Minimum supported client 	Windows 10, version 1703 [desktop apps only]
        Minimum supported server 	Windows Server 2016 [desktop apps only]

        typedef struct _TCP_INFO_v0 {
            TCPSTATE State;
            ULONG    Mss;
            ULONG64  ConnectionTimeMs;
            BOOLEAN  TimestampsEnabled;
            ULONG    RttUs;
            ULONG    MinRttUs;
            ULONG    BytesInFlight;
            ULONG    Cwnd;
            ULONG    SndWnd;
            ULONG    RcvWnd;
            ULONG    RcvBuf;
            ULONG64  BytesOut;
            ULONG64  BytesIn;
            ULONG    BytesReordered;
            ULONG    BytesRetrans;
            ULONG    FastRetrans;
            ULONG    DupAcksIn;
            ULONG    TimeoutEpisodes;
            UCHAR    SynRetrans;
        } TCP_INFO_v0, *PTCP_INFO_v0;
        """
        _fields_ = [
            ("State", ctypes.c_int),
            ("Mss", ctypes.wintypes.ULONG),
            ("ConnectionTimeMs", ctypes.c_uint64),
            ("TimestampsEnabled", ctypes.wintypes.BOOLEAN),
            ("RttUs", ctypes.wintypes.ULONG),
            ("MinRttUs", ctypes.wintypes.ULONG),
            ("BytesInFlight", ctypes.wintypes.ULONG),
            ("Cwnd", ctypes.wintypes.ULONG),
            ("SndWnd", ctypes.wintypes.ULONG),
            ("RcvWnd", ctypes.wintypes.ULONG),
            ("RcvBuf", ctypes.wintypes.ULONG),
            ("BytesOut", ctypes.c_uint64),
            ("BytesIn", ctypes.c_uint64),
            ("BytesReordered", ctypes.wintypes.ULONG),
            ("BytesRetrans", ctypes.wintypes.ULONG),
            ("FastRetrans", ctypes.wintypes.ULONG),
            ("DupAcksIn", ctypes.wintypes.ULONG),
            ("TimeoutEpisodes", ctypes.wintypes.ULONG),
            ("SynRetrans", ctypes.c_uint8),
        ]

    # WSAIoctl function (https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsaioctl)
    WSAIoctl_Fn = ctypes.windll.ws2_32.WSAIoctl
    WSAIoctl_Fn.argtypes = [
        ctypes.c_void_p,                            # [in]  SOCKET  s
        ctypes.wintypes.DWORD,                      # [in]  DWORD   dwIoControlCode
        ctypes.c_void_p,                            # [in]  LPVOID  lpvInBuffer
        ctypes.wintypes.DWORD,                      # [in]  DWORD   cbInBuffer
        ctypes.c_void_p,                            # [out] LPVOID  lpvOutBuffer
        ctypes.wintypes.DWORD,                      # [in]  DWORD   cbOutBuffer
        ctypes.POINTER(ctypes.wintypes.DWORD),      # [out] LPWORD  lpcbBytesReturned
        ctypes.c_void_p,                            # [in]  LPWSAOVERLAPPED lpOverlapped
        ctypes.c_void_p,                            # [in]  LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine
    ]
    WSAIoctl_Fn.restype = ctypes.c_int              # int

    def wait_ack(s: socket.socket):
        """
        Windows compatible wait_ack implementation.

        Waits until TCP_INFO_v0.BytesInFlight is zero.
        Raises RuntimeError if ACK_TIMEOUT exceeded
        """
        timeout = time.time() + ACK_TIMEOUT

        sockfd = ctypes.c_void_p(s.fileno())
        # SIO_TCP_INFO
        dwIoControlCode = ctypes.wintypes.DWORD(
            1 << 31 # IOC_IN
            |
            1 << 30 # IOC_OUT
            |
            3 << 27 # IOC_VENDOR?
            |
            39
        )
        infoVersion = ctypes.wintypes.DWORD(0)
        tcpinfo = TCP_INFO_v0()
        bytesReturned = ctypes.wintypes.DWORD(0)

        unacked = 1
        while unacked > 0:
            # Check timeout
            if time.time() > timeout:
                raise RuntimeError("ACK timeout")

            # Fetch TCP_INFO_v0
            res = WSAIoctl_Fn(
                sockfd,
                dwIoControlCode,
                ctypes.pointer(infoVersion),
                ctypes.wintypes.DWORD(ctypes.sizeof(infoVersion)),
                ctypes.pointer(tcpinfo),
                ctypes.wintypes.DWORD(ctypes.sizeof(tcpinfo)),
                ctypes.pointer(bytesReturned),
                None,
                None
            )
            assert res == 0

            unacked = tcpinfo.BytesInFlight
elif sys.platform == "darwin":
    """
    SO_NWRITE returns the amount of data in the output buffer not yet sent by the protocol.

    /Library/Developer/CommandLineTools/SDKs/MacOSX13.3.sdk/usr/include/sys/socket.h
    #define SO_NWRITE       0x1024          /* APPLE: Get number of bytes currently in send socket buffer */
    """
    SO_NWRITE = 0x1024

    def wait_ack(s: socket.socket):
        """
        MacOS compatible wait_ack implementation.

        Waits until SO_NWRITE is zero

        :param socket.socket s: The socket to check for unacked TCP packets
        :raises RuntimeError: if ACK_TIMEOUT exceeded
        """
        timeout = time.time() + ACK_TIMEOUT
        unacked = 1
        while unacked > 0:
            # Check timeout
            if time.time() > timeout:
                raise RuntimeError("ACK timeout")

            # Fecth SO_NWRITE
            unacked = s.getsockopt(
                socket.SOL_SOCKET,
                SO_NWRITE
            )
else:
    raise RuntimeError("Unsupported sys.platform")


def upload(firmware, host="192.168.0.50", port=80, path="/upgrade.cgi"):
    """
    Upload firmware to router

    :param str firmware: Firmware file path
    """

    assert os.path.isfile(firmware), f"File not found: firmware"
    # File size for Content-Length calculation
    fsize = os.stat(firmware).st_size

    # Connect to router with TCP_NODELAY
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.connect((host, port))

    print(f"Connection established to {host}:{port}")

    # Values for headers
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
    buffer = """POST {} HTTP/1.1
Host: {}
Content-Length: {}
Content-Type: multipart/form-data; boundary={}
Connection: Keep-Alive

""".format(path, host, content_length, boundary).replace("\n", "\r\n").encode()
    s.send(buffer)
    wait_ack(s)

    # Send multipart encapsulation boundary and headers
    buffer = """--{}
{}
{}

""".format(boundary, content_disposition, content_type).replace("\n", "\r\n").encode()
    s.send(buffer)
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
            #sys.exit(1)

    # Send ending boundary
    buffer = """
--{}--
""".format(boundary).replace("\n", "\r\n").encode()
    s.send(buffer)
    wait_ack(s)

    print()
    print("Firmware uploaded successfully")

    # Print response
    response = s.recv(4096).decode()
    print(response)
    # Check response contains "Upgrade successfully!"
    assert "Upgrade successfully!" in response

    # Wait some time before closing socket
    time.sleep(1)
    s.close()

    # COVR-P2500 firmwares logic
    # Increase percentage value every 2200ms and after 100% show ready message
    percent = 1
    while percent <= 100:
        print(f"Device is upgrading the firmware... {percent}%", end='\r')
        percent += 1
        time.sleep(2.2)
    print("Upgrade should now be successfully finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="D-Link COVR-P2500 flash utility",
        epilog="(C) 2023 Daniel Linjama"
    )
    parser.add_argument("firmware", type=str, help="Firmware file to upload")
    parser.add_argument("--host", type=str, default="192.168.0.50", help="Router IP address (default: 192.168.0.50)")
    parser.add_argument("--port", type=int, default=80, help="Router HTTP port (default: 80)")
    parser.add_argument("--path", type=str, default="/upgrade.cgi", help="HTTP path for firmware upgrade (default: /upgrade.cgi)")

    args = parser.parse_args()

    upload(args.firmware, args.host, args.port, args.path)
