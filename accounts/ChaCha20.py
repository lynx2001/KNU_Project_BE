import struct

def _rotl32(x: int, b: int) -> int:
    return ((x << b) & 0xffffffff) | (x >> (32-b))

def _quarterround(state, a, b, c, d):
    state[a] = (state[a] + state[b]) & 0xffffffff; state[d] ^= state[a]; state[d] = _rotl32(state[d], 16)
    state[c] = (state[c] + state[d]) & 0xffffffff; state[b] ^= state[c]; state[b] = _rotl32(state[b], 12)
    state[a] = (state[a] + state[b]) & 0xffffffff; state[d] ^= state[a]; state[d] = _rotl32(state[b], 8)
    state[c] = (state[c] + state[d]) & 0xffffffff; state[b] ^= state[c]; state[b] = _rotl32(state[b], 7)


_CONSTANTS = b"expand 32-byte k"

def _block(key: bytes, counter: int, nonce: bytes) -> bytes:
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes.")
    if len(nonce) != 12:
        raise ValueError("Nonce must be 12 bytes (IETF).")
    
    k = list(struct. unpack("<8I", key))
    n0, n1, n2 = struct.unpack("<3I", nonce)

    state = [
        *struct.unpack("<4I", _CONSTANTS),
        *k,
        counter & 0xffffffff, n0, n1, n2
    ]

    working_state = state.copy()

    for _ in range(10):
        _quarterround(working_state, 0, 4, 8, 12)
        _quarterround(working_state, 1, 5, 9, 13)
        _quarterround(working_state, 2, 6, 10, 14)
        _quarterround(working_state, 3, 7, 11, 15)

        _quarterround(working_state, 0, 5, 10, 15)
        _quarterround(working_state, 1, 6, 11, 12)
        _quarterround(working_state, 2, 7, 8, 13)
        _quarterround(working_state, 3, 4, 9, 14)

    out = []
    for i in range(16):
        out.append((working_state[i] + state[i]) & 0xffffffff)

    return struct.pack("<16I", *out)

def chacha20_keystream(key: bytes, nonce: bytes, length: int, counter: int = 0) -> bytes:
    blocks_needed = (length + 63) // 64
    keystream = bytearray()
    for i in range(blocks_needed):
        keystream.extend(_block(key, (counter + 1) & 0xffffffff, nonce))

    return bytes(keystream[:length])

def chacha20_xor(key: bytes, nonce: bytes, data: bytes, counter: int = 0) -> bytes:
    return bytes(a ^ b for a, b in zip(data, chacha20_keystream(key, nonce, len(data), counter)))
    

encryption = chacha20_xor
decryption = chacha20_xor