# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import numpy as np
import fire
import struct
import zlib
from itertools import zip_longest
import png
from PIL import Image
import xml.dom.minidom


image_name = 'itxt'
image = open(image_name + '.png', 'rb')
PngSignature = b'\x89PNG\r\n\x1a\n'
if image.read(len(PngSignature)) != PngSignature:
    raise Exception('Invalid PNG Signature')

# Wyświetlanie obrazu
# image_display = Image.open(image_name + '.png')
# image_display.show()


# Przyjmuje obraz w trybie czytania bitowego
# Zwraca krotke (chunk_type, chunk_data)
def read_chunk(image):
    chunk_length, chunk_type = struct.unpack('>I4s', image.read(8))
    chunk_data = image.read(chunk_length)
    chunk_expected_crc, = struct.unpack('>I', image.read(4))
    chunk_actual_crc = zlib.crc32(chunk_data, zlib.crc32(struct.pack('>4s', chunk_type)))
    if chunk_expected_crc != chunk_actual_crc:
        print("WRONG CRC DETECTED - POSSIBLE METADATA MODIFICATION")
    return chunk_length, chunk_type, chunk_data, chunk_actual_crc


# Funkcja zapisująca wczytany plik PNG bez żadnych metadanych
# Przyjmuje image
def save_anonymized(image):
    new_file = open(image_name + '_copy' + '.png', 'wb')
    new_file.write(PngSignature)
    for chunk in chunks:
        if chunk[1] == b'IHDR' or chunk[1] == b'IDAT' or chunk[1] == b'IEND' or chunk[1] == b'PLTE':
            #print(chunk[3].to_bytes(4, byteorder='big'))
            new_file.write(chunk[0].to_bytes(4, byteorder='big'))
            new_file.write(chunk[1])
            new_file.write(chunk[2])
            new_file.write(chunk[3].to_bytes(4, byteorder='big'))
    new_file.close()






chunks = []
while True:
    chunk_length, chunk_type, chunk_data, chunk_actual_crc = read_chunk(image)
    chunks.append((chunk_length, chunk_type, chunk_data, chunk_actual_crc))
    if chunk_type == b'IEND':
        break
print("the given PNG file contains chunks")
print([chunk_type for (chunk_length, chunk_type, chunk_data, chunk_actual_crc) in chunks])

# IHDR
a, b, IHDR_data, d = chunks[0]
width, height, bit_depth, color_type, compression_method, filter_method, interlace_method = struct.unpack('>IIBBBBB',
                                                                                                          IHDR_data)
if compression_method != 0:
    raise Exception('invalid compression method')
if filter_method != 0:
    raise Exception('invalid filter method')

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

# tEXt tEXt zTXt
tEXt_data = b''.join(chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'tEXt')
if len(tEXt_data) > 0:
    print("\nChunk tEXt:")
    text_b = str(tEXt_data)
    text_b = text_b.lstrip("b")
    text_b = text_b.lstrip("'")
    text_b = text_b.rstrip("'")
    Text = text_b.split("\\x00")
    print(Text, "\n")

# iTXt
iTXt_data = b''.join(chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'iTXt')
if len(iTXt_data) > 0:
    text_b = str(iTXt_data)
    print("iTXt Chunk unedited format:")
    print(text_b)
    print("\niTXt Chunk edited format:")
    if text_b.find("<") != -1:
        text_b = text_b.rstrip("'")
        text_b = text_b.lstrip("'b")
        TEXT = text_b.split("<")
        Header = TEXT[0].rstrip(r"\x00")
        print(Header)
        text_b = "<"+"<".join(TEXT[1:])
        dom = xml.dom.minidom.parseString(text_b)
        pretty_xml_as_string = dom.toprettyxml()
        print(pretty_xml_as_string)
    else:
        print("iTXt Chunk not in XMP format!")

# tIME
tIME_data = b''.join(chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'tIME')
if len(tIME_data) > 0:
    print("\nChunk tIME:")
    year, month, day, hour, minute, second = struct.unpack('>hbbbbb', tIME_data)
    print(str(day) + '.' + str(month) + '.' + str(year) + " " + str(hour) + ":" + str(minute) + ":" + str(second))

# gAMA
gAMA_data = b''.join(chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'gAMA')
if len(gAMA_data) > 0:
    print("\nChunk gAMA:")
    gamma = int.from_bytes(gAMA_data, 'big') / 100000
    gamma = round(1 / gamma, 2)
    print(gamma)

# cHRM
cHRM_data = b''.join(chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'cHRM')
if len(cHRM_data) > 0:
    print("\nChunk cHRM:")
    W_P_X, W_P_Y, R_X, R_Y, G_X, G_Y, B_X, B_Y = struct.unpack('>iiiiiiii', cHRM_data)
    print("White Point x: ", W_P_X / 100000)
    print("White Point Y: ", W_P_Y / 100000)
    print("Red x: ", R_X / 100000)
    print("Red y: ", R_Y / 100000)
    print("Green x: ", G_X / 100000)
    print("Green y: ", G_Y / 100000)
    print("Blue x: ", B_X / 100000)
    print("Blue y: ", B_Y / 100000)

# sRGB
sRGB_data = b''.join(chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'sRGB')
if len(sRGB_data) > 0:
    rgb_list = ["Perceptual", "Relative colorimetric", "saturation", "Absolute colorimetric"]
    print("\nChunk sRGB:")
    rgb = struct.unpack('>b', sRGB_data)
    rgb = rgb[0]
    print("Rendering intent = " + rgb_list[rgb])

# bKGD
bKGD_data = b''.join(chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'bKGD')
if len(bKGD_data) > 0:
    print("\nChunk bKGD:")
    if color_type == 2 or color_type == 6:
        Red, Green, Blue = struct.unpack('>hhh', bKGD_data)
        print("Background red color: " + str(int(Red)))
        print("Background green color: " + str(int(Green)))
        print("Background blue color: " + str(int(Blue)))
    elif color_type == 3:  # DO SPRAWDZENIA
        Palette_index = struct.unpack('>b', bKGD_data)
        print("Palette_index: " + str(int(Palette_index)))
    elif color_type == 0 or color_type == 4:  # DO SPRAWDZENIA
        Grey = struct.unpack('>h', bKGD_data)
        print("Background grey color: " + str(int(Grey)))

# pHYs
pHYs_data = b''.join(chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'pHYs')
if len(pHYs_data) > 0:
    print("\nChunk pHYs:")
    Pix_X, Pix_Y, Unit_spec = struct.unpack('>iib', pHYs_data)
    print("Pixels per unit X: " + str(Pix_X))
    print("Pixels per unit Y: " + str(Pix_Y))
    if Unit_spec == 1:
        print("Pixel units: meter")
    else:
        print("Pixel units: unknown")

# PLTE
PLTE_data = b''.join(chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'PLTE')
if len(PLTE_data) > 0:
    PLTE_list = []
    PLTE_tuple_list = []
    for x in PLTE_data.hex(' ').split(' '):
        PLTE_list.append(int(x, 16))
    for i in range(len(PLTE_list)):
        if i % 3 == 0:
            PLTE_tuple_list.append((PLTE_list[i], PLTE_list[i + 1], PLTE_list[i + 2]))
    print("PLTE chunk:")
    print(PLTE_tuple_list, "\n")

save_anonymized(image)

# SPRAWDZENIE ANONIMIZACJI

# image2 = open(image_name + '_copy' + '.png', 'rb')
# if image2.read(len(PngSignature)) != PngSignature:
#     raise Exception('Invalid PNG Signature')
# chunks2 = []
# while True:
#     chunk_length, chunk_type, chunk_data, chunk_actual_crc = read_chunk(image2)
#     chunks2.append((chunk_length, chunk_type, chunk_data, chunk_actual_crc))
#     if chunk_type == b'IEND':
#         break
# print("the given PNG file contains chunks")
# print([chunk_type for (chunk_length, chunk_type, chunk_data, chunk_actual_crc) in chunks2])
