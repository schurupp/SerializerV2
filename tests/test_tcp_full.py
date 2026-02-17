
import unittest
import socket
import threading
import time
import struct
from tests.common import KitchenSinkBinary, fuzz_binary
from serializer_core import StreamHandler

HOST = '127.0.0.1'
PORT = 9999

class TestTCPFull(unittest.TestCase):
    def setUp(self):
        self.server_ready = threading.Event()
        self.received_data = []
        self.server_thread = threading.Thread(target=self.run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.server_ready.wait(timeout=1.0)

    def run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            self.server_ready.set()
            conn, addr = s.accept()
            with conn:
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    self.received_data.append(chunk)

    def test_full_cycle(self):
        # 1. Prepare Message
        client_msg = KitchenSinkBinary()
        fuzz_binary(client_msg)
        
        # Manually set smart fields to ensure stability/predictability if needed
        # But KitchenSink definition has is_timestamp=True, is_checksum=True.
        # Serialization will trigger auto-update.
        
        # Serialize
        payload = client_msg.serialize()
        print(f"DEBUG: Payload size: {len(payload)} bytes")
        
        # 2. Send over TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(payload)
            
        # Wait slightly for server to process
        time.sleep(0.1)
        
        # 3. Reconstruct
        full_data = b''.join(self.received_data)
        self.assertEqual(len(full_data), len(payload), "Data loss or incomplete reception")
        
        # Deserialize
        server_msg, consumed = KitchenSinkBinary.from_bytes(full_data)
        
        # 4. Verify EVERYTHING
        print("Verifying Primitives...")
        self.assertEqual(server_msg.u8_val, client_msg.u8_val)
        self.assertEqual(server_msg.u16_val, client_msg.u16_val)
        self.assertEqual(server_msg.u32_val, client_msg.u32_val)
        self.assertEqual(server_msg.u64_val, client_msg.u64_val)
        self.assertEqual(server_msg.s8_val, client_msg.s8_val)
        self.assertEqual(server_msg.s16_val, client_msg.s16_val)
        self.assertEqual(server_msg.s32_val, client_msg.s32_val)
        self.assertEqual(server_msg.s64_val, client_msg.s64_val)
        
        print("Verifying Floats...")
        self.assertAlmostEqual(server_msg.f4_val, client_msg.f4_val, places=4)
        self.assertAlmostEqual(server_msg.f8_val, client_msg.f8_val, places=6)
        
        print("Verifying BitFields...")
        # LSB
        self.assertEqual(server_msg.flags_lsb['enable'], client_msg.flags_lsb['enable'])
        self.assertEqual(server_msg.flags_lsb['mode'], client_msg.flags_lsb['mode'])
        self.assertEqual(server_msg.flags_lsb['color'], client_msg.flags_lsb['color'])
        # MSB
        self.assertEqual(server_msg.flags_msb['valid'], client_msg.flags_msb['valid'])
        self.assertEqual(server_msg.flags_msb['reserved'], client_msg.flags_msb['reserved'])
        
        print("Verifying Fixed Point...")
        self.assertAlmostEqual(server_msg.fp_u, client_msg.fp_u, delta=0.1)
        self.assertAlmostEqual(server_msg.fp_s, client_msg.fp_s, delta=0.1)
        self.assertAlmostEqual(server_msg.fp_dm, client_msg.fp_dm, delta=0.1)
        
        print("Verifying Arrays...")
        self.assertEqual(list(server_msg.scores), list(client_msg.scores))
        self.assertEqual(len(server_msg.items), len(client_msg.items))
        for i, item in enumerate(client_msg.items):
            self.assertEqual(server_msg.items[i].id, item.id)
            self.assertAlmostEqual(server_msg.items[i].value, item.value, places=4)
            
        # Checksum and Length
        # Server message deserialized from payload, so it should have exact same CRC/Length as payload
        self.assertEqual(server_msg.msg_len, client_msg.msg_len) # client_msg.msg_len was updated during serialize
        self.assertEqual(server_msg.crc, client_msg.crc)
        
        # Timestamp (if resolution is high enough to capture diff? or exact match?)
        # Since client_msg updated its ts during serialize, and server deserialized it...
        self.assertEqual(server_msg.ts, client_msg.ts)
        
        print("SUCCESS: TCP Full Cycle Test Passed")

if __name__ == '__main__':
    unittest.main()
