import math
import sympy


def generate_keys(key_bit_size):
    p = sympy.randprime(pow(2, ((key_bit_size/2)-1)), pow(2, (key_bit_size/2)))
    q = sympy.randprime(pow(2, ((key_bit_size/2)-1)), pow(2, (key_bit_size/2)))
    n = p*q
    while n.bit_length() != key_bit_size:
        p = sympy.randprime(pow(2, ((key_bit_size / 2) - 1)), pow(2, (key_bit_size / 2)))
        q = sympy.randprime(pow(2, ((key_bit_size / 2) - 1)), pow(2, (key_bit_size / 2)))
        n = p * q

    theta = (p-1)*(q-1)

    e = 65537
    while math.gcd(e, theta) != 1:
        e = e + 1

    d = pow(e, -1, theta)
    public_key = (e, n)
    private_key = (d, n)
    return public_key, private_key




