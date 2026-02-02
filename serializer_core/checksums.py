import zlib
import struct
from typing import Callable

def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF

def crc16(data: bytes) -> int:
    """
    CRC-16-CCITT (0xFFFF init, 0x1021 poly).
    Common in many protocols.
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
        crc &= 0xFFFF
    return crc

def xor_sum(data: bytes) -> int:
    result = 0
    for b in data:
        result ^= b
    return result

def byte_sum(data: bytes) -> int:
    """Sum of bytes modulo 256."""
    return sum(data) & 0xFF

def byte_sum_ones_complement(data: bytes) -> int:
    """Inverse of byte sum (0xFF - sum)."""
    s = sum(data) & 0xFF
    return (~s) & 0xFF

def byte_sum_twos_complement(data: bytes) -> int:
    """Two's complement of sum (0x100 - sum). Sum + Checksum = 0."""
    s = sum(data) & 0xFF
    return (0x100 - s) & 0xFF

def additive_word(data: bytes) -> int:
    """Sum of 16-bit words (Big Endian implicit usually, or native?). 
    We'll assume Little Endian packing as per system default, 
    but word sum is often agnostic or BE. 
    Let's sum as 16-bit integers."""
    # Pad if odd length
    if len(data) % 2 != 0:
        data += b'\x00'
    
    total = 0
    for i in range(0, len(data), 2):
        word = (data[i+1] << 8) | data[i] # Little Endian interpretation?
        # Or should we just simple add values?
        # "Additive Word" usually means summing 16-bit values.
        # Let's assume Little Endian words for now.
        total += word
    
    return total & 0xFFFF

ALGOS = {
    'CRC32': crc32,
    'CRC16': crc16,
    'XOR': xor_sum,
    'ByteSum': byte_sum,
    'ByteSum1C': byte_sum_ones_complement,
    'ByteSum2C': byte_sum_twos_complement,
    'AdditiveWord': additive_word
}

def calculate(algo_name: str, data: bytes) -> int:
    func = ALGOS.get(algo_name)
    if func:
        return func(data)
    return 0
