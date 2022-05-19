import os
from Random_Key_Generator import *
from collections import deque
from main import *
import png

key_size = 1024
# all encrypted data blocks has the length of the key
encrypted_block_size = key_size // 8
# data block has to be smaller than key
data_block_size = key_size // 8 - 1


def get_main_file_info(chunks):
    a, b, IHDR_data, d = chunks[0]
    width, height, bit_depth, color_type, compression_method, filter_method, interlace_method = struct.unpack(
        '>IIBBBBB',
        IHDR_data)
    if compression_method != 0:
        raise Exception('invalid compression method')
    if filter_method != 0:
        raise Exception('invalid filter method')

    Color_Types = []
    Color_Types.append((0, "Grayscale", 1))
    Color_Types.append((2, "Truecolor", 3))
    Color_Types.append((3, "Indexed-color", 1))
    Color_Types.append((4, "Grayscale with alpha", 2))
    Color_Types.append((6, "Truecolor with alpha", 4))

    for Type in Color_Types:
        if color_type == Type[0]:
            color_type_bpp = Type[2]

    return width, height, color_type_bpp


def get_IDAT_data(chunks):
    IDAT_data = b''.join(chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'IDAT')
    return IDAT_data


def convert_IDAT_data(IDAT_data, width, height, bpp):
    image_bytes = []

    def recon_a(r, c, image_bytes):
        return image_bytes[r * (width * bpp) + c - bpp] if c >= bpp else 0

    def recon_b(r, c, image_bytes):
        return image_bytes[(r - 1) * (width * bpp) + c] if r > 0 else 0

    def recon_c(r, c, image_bytes):
        return image_bytes[
            (r - 1) * (width * bpp) + c - bpp] if r > 0 and c >= bpp else 0

    if len(IDAT_data) > 0:
        decompressed_test = zlib.decompress(IDAT_data)
        print("\nExpected length:" + str(height * (1 + width * bpp)) + "\nActual length:" + str(
            len(decompressed_test)))

        for r in range(height):
            row_filter = decompressed_test[r * (1 + width * bpp)]
            for c in range(width * bpp):
                if (row_filter == 0):
                    image_bytes.append(0xff & int(decompressed_test[1 + c + (1 + width * bpp) * r]))
                elif (row_filter == 1):
                    image_bytes.append(0xff & int(
                        (decompressed_test[1 + c + (1 + width * bpp) * r] + recon_a(r, c, image_bytes))))
                elif (row_filter == 2):
                    image_bytes.append(0xff &
                                       int(decompressed_test[1 + c + (1 + width * bpp) * r] +
                                           recon_b(r, c, image_bytes)))
                elif row_filter == 3:
                    image_bytes.append(0xff &
                                       int(decompressed_test[1 + c + (1 + width * bpp) * r] + (
                                               recon_a(r, c, image_bytes)
                                               + recon_b(r, c, image_bytes)) // 2))
                elif (row_filter == 4):
                    image_bytes.append(0xff & int(decompressed_test[1 + c + (1 + width * bpp) * r] +
                                                  paeth_predictor(recon_a(r, c, image_bytes),
                                                                  recon_b(r, c, image_bytes),
                                                                  recon_c(r, c, image_bytes))))
    return image_bytes


def encrypt_ecb(data, public_key):
    encrypted_data = []
    for i in range(0, len(data), data_block_size):

        block_to_encrypt_hex = bytes(data[i: i + data_block_size])
        block_to_encrypt_int = int.from_bytes(block_to_encrypt_hex, 'big')

        cipher_int = pow(block_to_encrypt_int, public_key[0], public_key[1])

        cipher_hex = cipher_int.to_bytes(encrypted_block_size, 'big')

        for i in range(encrypted_block_size):
            encrypted_data.append(cipher_hex[i])
    return encrypted_data




def get_png_writer(width, height, bytes_per_pixel):
    if bytes_per_pixel == 1:
        png_writer = png.Writer(width, height, greyscale=True)
    elif bytes_per_pixel == 2:
        png_writer = png.Writer(width, height, greyscale=True, alpha=True)
    elif bytes_per_pixel == 3:
        png_writer = png.Writer(width, height, greyscale=False)
    elif bytes_per_pixel == 4:
        png_writer = png.Writer(width, height, greyscale=False, alpha=True)

    return png_writer


def save_encrypted_png(encrypted_data, original_length, width, height, bytes_per_pixel, encrypted_file_name):
    png_writer = get_png_writer(width, height, bytes_per_pixel)

    idat_data, after_iend_data = separate_after_iend_data(encrypted_data, original_length)
    bytes_row_width = width * bytes_per_pixel
    data_in_rows = [idat_data[i: i + bytes_row_width] for i in range(0, len(idat_data), bytes_row_width)]

    new_file = open("tmp" + '.png', 'wb')
    png_writer.write(new_file, data_in_rows)
    new_file.write(bytes(after_iend_data))
    new_file.close()

    original_chunks, x = get_chunks_and_after_IEND_data(image_name)
    encrypted_chunks, x = get_chunks_and_after_IEND_data("tmp")
    os.remove('tmp.png')

    new_file = open(encrypted_file_name + '.png', 'wb')
    new_file.write(png_signature)
    idat_finish = False

    for chunk in original_chunks:
        if chunk[1] == b'IDAT' and idat_finish is False:
            for enrypted_chunk in encrypted_chunks:
                if enrypted_chunk[1] == b'IDAT':
                    new_file.write(enrypted_chunk[0].to_bytes(4, byteorder='big'))
                    new_file.write(enrypted_chunk[1])
                    new_file.write(enrypted_chunk[2])
                    new_file.write(enrypted_chunk[3].to_bytes(4, byteorder='big'))
            idat_finish = True
        else:
            new_file.write(chunk[0].to_bytes(4, byteorder='big'))
            new_file.write(chunk[1])
            new_file.write(chunk[2])
            new_file.write(chunk[3].to_bytes(4, byteorder='big'))
    new_file.write(bytes(after_iend_data))
    new_file.close()


def separate_after_iend_data(data, original_length):
    data = deque(data)
    idat_data = []
    after_iend_data = []
    for i in range(original_length):
        idat_data.append(data.popleft())
    for i in range(len(data)):
        after_iend_data.append(data.popleft())
    return idat_data, after_iend_data


def decrypt_ecb(data, after_iend_data, private_key, original_data_len):
    encrypted_data = connect_data(data, after_iend_data)
    decrypted_data = []

    for i in range(0, len(encrypted_data), encrypted_block_size):
        encrypted_hex_block = bytes(encrypted_data[i: i + encrypted_block_size])

        decrypted_int = pow(int.from_bytes(encrypted_hex_block, 'big'), private_key[0], private_key[1])

        # if it's the last block with added zero's - change bytes length
        if len(decrypted_data) + data_block_size > original_data_len:
            decrypted_hex_len = original_data_len - len(decrypted_data)
        else:
            decrypted_hex_len = data_block_size

        decrypted_hex = decrypted_int.to_bytes(decrypted_hex_len, 'big')

        for byte in decrypted_hex:
            decrypted_data.append(byte)

    return decrypted_data


def connect_data(data, after_iend_data):
    encrypted_data = []

    for i in range(0, len(data), data_block_size):
        encrypted_data.extend(data[i:i + data_block_size])
    for i in range(0, len(after_iend_data), data_block_size):
        encrypted_data.extend(after_iend_data[i:i + data_block_size])

    return encrypted_data


def create_decrypted_png(metadata_chunks, decrpted_data, width, height, bytes_per_pixel, decrypted_image_name):
    png_writer = get_png_writer(width, height, bytes_per_pixel)
    bytes_row_width = width * bytes_per_pixel
    data_in_rows = [decrpted_data[i: i + bytes_row_width] for i in
                              range(0, len(decrpted_data), bytes_row_width)]
    f = open("tmp.png", 'wb')
    png_writer.write(f, data_in_rows)
    f.close()
    decrypted_chunks, x = get_chunks_and_after_IEND_data("tmp")
    os.remove('tmp.png')

    decrypted_file = open(decrypted_image_name + '.png', 'wb')
    decrypted_file.write(png_signature)
    idat_finish = False

    for chunk in metadata_chunks:
        if chunk[1] == b'IDAT' and idat_finish is False:
            for decrypted_chunk in decrypted_chunks:
                if decrypted_chunk[1] == b'IDAT':
                    decrypted_file.write(decrypted_chunk[0].to_bytes(4, byteorder='big'))
                    decrypted_file.write(decrypted_chunk[1])
                    decrypted_file.write(decrypted_chunk[2])
                    decrypted_file.write(decrypted_chunk[3].to_bytes(4, byteorder='big'))
            idat_finish = True
        else:
            decrypted_file.write(chunk[0].to_bytes(4, byteorder='big'))
            decrypted_file.write(chunk[1])
            decrypted_file.write(chunk[2])
            decrypted_file.write(chunk[3].to_bytes(4, byteorder='big'))
    decrypted_file.close()


image_name = 'spiderman'
public_key, private_key = generate_keys(key_size)

#ENCRYPTING
chunks, x = get_chunks_and_after_IEND_data(image_name)
width, height, bits_per_pixel = get_main_file_info(chunks)
data = get_IDAT_data(chunks)
converted_data = convert_IDAT_data(data, width, height, bits_per_pixel)
cipher = encrypt_ecb(converted_data, public_key)
original_length = len(converted_data)
save_encrypted_png(cipher, original_length, width, height, bits_per_pixel, image_name+"_encrypted")

#DECRYPTING
chunks, x = get_chunks_and_after_IEND_data(image_name+"_encrypted")
width, height, bits_per_pixel = get_main_file_info(chunks)
data = get_IDAT_data(chunks)
converted_data = convert_IDAT_data(data, width, height, bits_per_pixel)
decrypted_data = decrypt_ecb(converted_data, x, private_key, original_length)
create_decrypted_png(chunks, decrypted_data, width, height, bits_per_pixel, image_name+"_decrypted")

