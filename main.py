# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import numpy as np
import fire
import struct
import zlib

image = open('dog.png', 'rb')
PngSignature = b'\x89PNG\r\n\x1a\n'
if image.read(len(PngSignature)) != PngSignature:
    raise Exception('Invalid PNG Signature')


def read_chunk(f):
    # Returns (chunk_type, chunk_data)
    chunk_length, chunk_type = struct.unpack('>I4s', f.read(8))
    chunk_data = image.read(chunk_length)
    chunk_expected_crc, = struct.unpack('>I', f.read(4))
    chunk_actual_crc = zlib.crc32(chunk_data, zlib.crc32(struct.pack('>4s', chunk_type)))
    if chunk_expected_crc != chunk_actual_crc:
        raise Exception('chunk checksum failed')
    return chunk_type, chunk_data


chunks = []
while True:
    chunk_type, chunk_data = read_chunk(image)
    chunks.append((chunk_type, chunk_data))
    if chunk_type == b'IEND':
        break
print("the given PNG file contains chunks")
print([chunk_type for (chunk_type, chunk_data) in chunks])

# IHDR
_, IHDR_data = chunks[0]
width, height, bit_depth, color_type, compression_method, filter_method, interlace_method = struct.unpack('>IIBBBBB', IHDR_data)
if compression_method != 0:
    raise Exception('invalid compression method')
if filter_method != 0:
    raise Exception('invalid filter method')
# if color_type != 6:
#     raise Exception('we only support truecolor with alpha')
# if bit_depth != 8:
#     raise Exception('we only support a bit depth of 8')
# if interlace_method != 0:
#     raise Exception('we only support no interlacing')

Color_Types = []
Color_Types.append((0, "Grayscale"))
Color_Types.append((2, "Truecolor"))
Color_Types.append((3, "Indexed-color"))
Color_Types.append((4, "Grayscale with alpha"))
Color_Types.append((6, "Truecolor with alpha"))

for Type in Color_Types:
    if color_type == Type[0]:
        color_type_string = Type[1]





print("\nChunk IHDR:")
print("Width = ", width)
print("Height = ", height)
print("Bit depth = ", bit_depth)
print("Color type = ", color_type, "- ", color_type_string)
print("Compression method = ", compression_method)
print("Filter method = ", filter_method)
print("Interlace method = ", interlace_method, "\n")
