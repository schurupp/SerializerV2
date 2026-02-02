import sys
import os
import socket
import threading
import time
import collections
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from serializer_core import *
from Messages import *

# Reuse TestMessage from integration test or define simple one
@register
class SimpleMsg(Message):
    # Discriminator required for StreamHandler/Registry auto-detection
    disc = UInt8(is_discriminator=True, default=0xBB)
    val_a = UInt32()
    val_b = UInt32()

HOST = '127.0.0.1'
PORT = 9999
MSG_COUNT = 500

def run_server(stop_event, ready_event):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # ... (rest of server)
    # Make sure to keep the PASS/FAIL logic but remove the buffer dump

    server_sock.bind((HOST, PORT))
    server_sock.listen(1)
    
    print("[Server] Listening...")
    ready_event.set()
    
    conn, addr = server_sock.accept()
    print(f"[Server] Connected by {addr}")
    
    handler = StreamHandler()
    dq = collections.deque()
    
    received_count = 0
    
    try:
        while not stop_event.is_set():
            data = conn.recv(1024)
            if not data:
                break
            
            # Feed stream
            handler.feed(data, dq)
            
            # Process Queue
            while dq:
                msg = dq.popleft()
                received_count += 1
                
                # Debug Logging for first 5 and every 100th
                if received_count <= 5 or received_count % 100 == 0:
                    print(f"[Server] Msg {received_count}: {msg.__class__.__name__}")
                    # Print all public fields
                    for key, value in vars(msg).items():
                        if not key.startswith('_'):
                            print(f"    {key}: {value}")
                    print("-" * 20)

            if received_count >= MSG_COUNT:
                print("[Server] Target count reached.")
                break
                
    finally:
        print(f"[Server] Loop ended. Received: {received_count}. Queue size: {len(dq)}")
        
        conn.close()
        server_sock.close()
        
    print(f"[Server] Final Count: {received_count} / {MSG_COUNT}")
    if received_count == MSG_COUNT:
        print("PASS: Received all messages.")
    else:
        print(f"FAIL: Count mismatch! {received_count} != {MSG_COUNT}")
        sys.exit(1)

def run_client(ready_event):
    ready_event.wait() # Wait for server
    time.sleep(0.1) 
    
    print("[Client] Connecting...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    
    print(f"[Client] Sending {MSG_COUNT} messages...")
    
    # Pre-pack
    data_buffer = bytearray()
    for i in range(MSG_COUNT):
        m = TestMsg()
        # Set dynamic timestamp to verify it works
        data_buffer.extend(m.serialize())
        
    sock.sendall(data_buffer)
    print("[Client] Sent all data.")
    sock.close()

def run_tcp_demo():
    stop_event = threading.Event()
    ready_event = threading.Event()
    
    server_thread = threading.Thread(target=run_server, args=(stop_event, ready_event))
    client_thread = threading.Thread(target=run_client, args=(ready_event,))
    
    server_thread.start()
    client_thread.start()
    
    client_thread.join()
    server_thread.join()
    
    print("TCP Demo Completed.")

if __name__ == "__main__":
    run_tcp_demo()
