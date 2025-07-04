from Crypto.Cipher import AES


def xor(s1, s2):
    """
    Exclusive-Or of two byte arrays

    Args:
        s1 (bytes): first set of bytes
        s2 (bytes): second set of bytes
    Returns:
        (bytes) s1 ^ s2
    Raises:
        ValueError if s1 and s2 lengths don't match
    """
    if len(s1) != len(s2):
        raise ValueError('Input not equal length, s1 is %d bytes and s2 is  %d bytes' % (len(s1), len(s2)))
    return bytes(a ^ b for a, b in zip(s1, s2))


def rotate(input_s, bytes_):
    """
    Rotate a string by a number of bytes

    Args:
        input_s (bytes): the input string
        bytes_ (int): the number of bytes to rotate by
    Returns:
        (bytes) s1 rotated by n bytes
    """
    return bytes(input_s[(i + bytes_) % len(input_s)] for i in range(len(
        input_s)))


def encrypt(k, buf, IV=16 * b'\x00'):
    """
    Rijndael (AES-128) cipher function used by Milenage

    Args:
        k (bytes): 128 bit encryption key
        buf (bytes): 128 bit buffer to encrypt
        IV (bytes): 128 bit initialization vector
    Returns:
        encrypted output
    """
    aes_cipher = AES.new(k, AES.MODE_CBC, IV)
    return aes_cipher.encrypt(buf)


def generate_opc(key, op):
    """
    Generate the OP_c according to 3GPP 35.205 8.2
    Args:
        key (bytes): 128 bit subscriber key
        op (bytes): 128 bit operator dependent value
    Returns:
        128 bit OP_c
    """
    opc = encrypt(key, op)
    return xor(opc, op)


def f1(key, sqn, rand, opc, amf):
    """
    Implementation of f1 and f1*, the network authentication function and
    the re-synchronisation message authentication function according to
    3GPP 35.206 4.1

    Args:
        key (bytes): 128 bit subscriber key
        sqn (bytes): 48 bit sequence number
        rand (bytes): 128 bit random challenge
        opc (bytes): 128 bit computed from OP and subscriber key
        amf (bytes): 16 bit authentication management field
    Returns:
        (64 bit Network auth code, 64 bit Resynch auth code)
    """
    # TEMP = E_K(RAND XOR OP_C)
    temp = encrypt(key, xor(rand, opc))

    # IN1 = SQN || AMF || SQN || AMF
    in1 = (sqn[0:6] + amf[0:2]) * 2

    # Constants from 3GPP 35.206 4.1
    c1 = 16 * b'\x00'  # some constant
    r1 = 8  # rotate by 8 bytes

    # OUT1 = E_K(TEMP XOR rotate(IN1 XOR OP_C, r1) XOR c1) XOR OP_C
    out1_ = encrypt(key, xor(temp, rotate(xor(in1, opc), r1)), c1)
    out1 = xor(opc, out1_)

    #  MAC-A = f1 = OUT1[0] .. OUT1[63]
    #  MAC-S = f1* = OUT1[64] .. OUT1[127]
    return out1[:8], out1[8:]


def f2(key, rand, opc):
    crypt_in = xor(rand, opc)
    temp = encrypt(key, crypt_in)

    crypt_in = xor(temp, opc)
    crypt_in = bytearray(crypt_in)
    crypt_in[15] ^= 1
    out = encrypt(key, crypt_in)

    out = xor(out, opc)
    res = out[8:16]

    return res


def f3(key, rand, opc):
    """
    Implementation of f3, the compute confidentiality key according
    to 3GPP 35.206 4.1

    Args:
        key (bytes): 128 bit subscriber key
        rand (bytes): 128 bit random challenge
        opc (bytes): 128 bit computed from OP and subscriber key
    Returns:
        ck, 128 bit confidentiality key
    """
    # Constants from 3GPP 35.206 4.1
    c3 = 15 * b'\x00' + b'\x02'  # some constant
    r3 = 4  # rotate by 4 bytes

    # TEMP = E_K(RAND XOR OP_C)
    # OUT3 = E_K(rotate(TEMP XOR OP_C, r3) XOR c3) XOR OP_C
    temp_x_opc = xor(encrypt(key, xor(rand, opc)), opc)
    out3 = xor(encrypt(key, xor(rotate(temp_x_opc, r3), c3)), opc)
    # ck = f3 = OUT3
    return out3


def f4(key, rand, opc):
    """
    Implementation of f4, the integrity key according
    to 3GPP 35.206 4.1

    Args:
        key (bytes): 128 bit subscriber key
        rand (bytes): 128 bit random challenge
        opc (bytes): 128 bit computed from OP and subscriber key
    Returns:
        ik, 128 bit integrity key
    """
    # Constants from 3GPP 35.206 4.1
    c4 = 15 * b'\x00' + b'\x04'  # some constant
    r4 = 8  # rotate by 8 bytes

    # TEMP = E_K(RAND XOR OP_C)
    # OUT4 = E_K(rotate(TEMP XOR OP_C, r4) XOR c4) XOR OP_C
    temp_x_opc = xor(encrypt(key, xor(rand, opc)), opc)
    out4 = xor(encrypt(key, xor(rotate(temp_x_opc, r4), c4)), opc)
    # ik = f4 = OUT4
    return out4


def f2_f5(key, rand, opc):
    """
    Implementation of f2 and f5, the compute anonymity key and response to
    challenge functions according to 3GPP 35.206 4.1

    Args:
        key (bytes): 128 bit subscriber key
        rand (bytes): 128 bit random challenge
        opc (bytes): 128 bit computed from OP and subscriber key
    Returns:
        (xres, ak) = (64 bit response to challenge, 48 bit anonymity key)
    """
    # Constants from 3GPP 35.206 4.1
    c2 = 15 * b'\x00' + b'\x01'  # some constant
    r2 = 0  # rotate by 0 bytes

    # TEMP = E_K(RAND XOR OP_C)
    # OUT2 = E_K(rotate(TEMP XOR OP_C, r2) XOR c2) XOR OP_C
    temp_x_opc = xor(encrypt(key, xor(rand, opc)), opc)
    out2 = xor(encrypt(key, xor(rotate(temp_x_opc, r2), c2)), opc)
    # res = f2 = OUT2[64] ... OUT2[127]
    # ak = f5 = OUT2[0] ... OUT2[47]
    return out2[8:16], out2[0:6]


def gsm_milenage_f2345(ki, opc, rand):
    '''Milenage f2, f3, f4, f5, f5* algorithms'''
    i = 0
    tmp1 = logical_xor(rand, opc)
    tmp2 = aes_encrypt(ki, tmp1)
    tmp1 = logical_xor(tmp2, opc)
    tmp1 = tmp1[:15] + chr(ord(tmp1[15]) ^ 1)
    tmp3 = aes_encrypt(ki, tmp1)
    tmp3 = logical_xor(tmp3, opc)
    res = tmp3[8:]

    # F3 - to calculate ck
    ck_map = {}
    for i in range(16):
        ck_map[(i + 12) % 16] = __XOR__(tmp2[i], opc[i])
    ck_map[15] = __XOR__(ck_map[15], chr(2))
    tmp1 = ''.join(val for val in ck_map.values())
    ck = aes_encrypt(ki, tmp1)
    ck = logical_xor(ck, opc)

    # F4 - to calculate ik
    ik_map = {}
    for i in range(16):
        ik_map[(i + 8) % 16] = __XOR__(tmp2[i], opc[i])
    ik_map[15] = __XOR__(ik_map[15], chr(4))
    tmp1 = ''.join(val for val in ik_map.values())
    ik = aes_encrypt(ki, tmp1)
    ik = logical_xor(ik, opc)

    return res, ck, ik


def gsm_milenage(ki, opc, rand):
    '''Generate GSM-Milenage (3GPP TS 55.205) auth triplet
       @ki  : 128-bit subscriber key
       @opc : 128-bit operator variant algorithm configuration
       @rand: 128-bit random challenge'''

    res, ck, ik = gsm_milenage_f2345(ki, opc, rand)

    # Calculate sres
    sres_map = {}
    for idx in range(4):
        sres_map[idx] = __XOR__(res[idx], res[idx + 4])
    sres = ''.join(val for val in sres_map.values())

    # Calculate kc
    kc_map = {}
    for idx in range(8):
        kc_map[idx] = __XOR__(__XOR__(ck[idx], ck[idx + 8]),
                              __XOR__(ik[idx], ik[idx + 8]))
    kc = ''.join(val for val in kc_map.values())

    return sres, kc
