import struct
import zlib
from PIL import Image
import xml.dom.minidom
import matplotlib.pyplot as plt
import numpy as np

png_signature = b'\x89PNG\r\n\x1a\n'

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
def save_anonymized(chunks, image_name):
    new_file = open(image_name + '.png', 'wb')
    new_file.write(png_signature)
    for chunk in chunks:
        if chunk[1] == b'IHDR' or chunk[1] == b'IDAT' or chunk[1] == b'IEND' or chunk[1] == b'PLTE' or chunk[
            1] == b'tRNS':
            # print(chunk[3].to_bytes(4, byteorder='big'))
            new_file.write(chunk[0].to_bytes(4, byteorder='big'))
            new_file.write(chunk[1])
            new_file.write(chunk[2])
            new_file.write(chunk[3].to_bytes(4, byteorder='big'))
    new_file.close()


def paeth_predictor(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    elif pb <= pc:
        return b
    else:
        return c


def get_chunks_and_after_IEND_data(image_name):
    image = open(image_name + '.png', 'rb')
    if image.read(len(png_signature)) != png_signature:
        raise Exception('Invalid PNG Signature')
    chunks = []
    while True:
        chunk_length, chunk_type, chunk_data, chunk_actual_crc = read_chunk(image)
        chunks.append((chunk_length, chunk_type, chunk_data, chunk_actual_crc))
        if chunk_type == b'IEND':
            break
    print("the given PNG file contains chunks")
    print([chunk_type for (chunk_length, chunk_type, chunk_data, chunk_actual_crc) in chunks])

    after_iend_data = bytes()
    while True:
        bytes_read = image.read(2)
        if not bytes_read:
            break
        after_iend_data += bytes_read
    image.close()
    return chunks, after_iend_data


def analyze_chunks(chunks):
    # IHDR
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
            color_type_string = Type[1]
            color_type_bpp = Type[2]

    print("\nChunk IHDR:")
    print("Width = ", width)
    print("Height = ", height)
    print("Bit depth = ", bit_depth)
    print("Color type = ", color_type, "- ", color_type_string)
    print("Compression method = ", compression_method)
    print("Filter method = ", filter_method)
    print("Interlace method = ", interlace_method, "\n")

    # tEXt tEXt zTXt
    tEXt_data = b''.join(
        chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'tEXt')
    if len(tEXt_data) > 0:
        print("\nChunk tEXt:")
        text_b = str(tEXt_data)
        text_b = text_b.lstrip("b")
        text_b = text_b.lstrip("'")
        text_b = text_b.rstrip("'")
        Text = text_b.split("\\x00")
        print(Text, "\n")

    # iTXt
    iTXt_data = b''.join(
        chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'iTXt')
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
            text_b = "<" + "<".join(TEXT[1:])
            dom = xml.dom.minidom.parseString(text_b)
            pretty_xml_as_string = dom.toprettyxml()
            print(pretty_xml_as_string)
        else:
            print("iTXt Chunk not in XMP format!")

    # tIME
    tIME_data = b''.join(
        chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'tIME')
    if len(tIME_data) > 0:
        print("\nChunk tIME:")
        year, month, day, hour, minute, second = struct.unpack('>hbbbbb', tIME_data)
        print(str(day) + '.' + str(month) + '.' + str(year) + " " + str(hour) + ":" + str(minute) + ":" + str(second))

    # gAMA
    gAMA_data = b''.join(
        chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'gAMA')
    if len(gAMA_data) > 0:
        print("\nChunk gAMA:")
        gamma = int.from_bytes(gAMA_data, 'big') / 100000
        gamma = round(1 / gamma, 2)
        print(gamma)

    # cHRM
    cHRM_data = b''.join(
        chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'cHRM')
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
    sRGB_data = b''.join(
        chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'sRGB')
    if len(sRGB_data) > 0:
        rgb_list = ["Perceptual", "Relative colorimetric", "saturation", "Absolute colorimetric"]
        print("\nChunk sRGB:")
        rgb = struct.unpack('>b', sRGB_data)
        rgb = rgb[0]
        print("Rendering intent = " + rgb_list[rgb])

    # bKGD
    bKGD_data = b''.join(
        chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'bKGD')
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
    pHYs_data = b''.join(
        chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'pHYs')
    if len(pHYs_data) > 0:
        print("\nChunk pHYs:")
        Pix_X, Pix_Y, Unit_spec = struct.unpack('>iib', pHYs_data)
        print("Pixels per unit X: " + str(Pix_X))
        print("Pixels per unit Y: " + str(Pix_Y))
        if Unit_spec == 1:
            print("Pixel units: meter")
        else:
            print("Pixel units: unknown")

    # tRNS (used only for type 3)
    tRNS_data = b''.join(
        chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'tRNS')

    # PLTE
    PLTE_data = bytearray(b''.join(
        chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'PLTE'))

    # IDAT
    IDAT_data = b''.join(
        chunk_data for chunk_length, chunk_type, chunk_data, chunk_actual_crc in chunks if chunk_type == b'IDAT')
    image_bytes = []

    def recon_a(r, c, image_bytes):
        return image_bytes[r * (width * color_type_bpp) + c - color_type_bpp] if c >= color_type_bpp else 0

    def recon_b(r, c, image_bytes):
        return image_bytes[(r - 1) * (width * color_type_bpp) + c] if r > 0 else 0

    def recon_c(r, c, image_bytes):
        return image_bytes[
            (r - 1) * (width * color_type_bpp) + c - color_type_bpp] if r > 0 and c >= color_type_bpp else 0

    if len(IDAT_data) > 0:
        decompressed_test = zlib.decompress(IDAT_data)
        print("\nExpected length:" + str(height * (1 + width * color_type_bpp)) + "\nActual length:" + str(
            len(decompressed_test)))

        for r in range(height):
            row_filter = decompressed_test[r * (1 + width * color_type_bpp)]
            for c in range(width * color_type_bpp):
                if (row_filter == 0):
                    image_bytes.append(0xff & int(decompressed_test[1 + c + (1 + width * color_type_bpp) * r]))
                elif (row_filter == 1):
                    image_bytes.append(0xff & int(
                        (decompressed_test[1 + c + (1 + width * color_type_bpp) * r] + recon_a(r, c, image_bytes))))
                elif (row_filter == 2):
                    image_bytes.append(0xff &
                                       int(decompressed_test[1 + c + (1 + width * color_type_bpp) * r] +
                                           recon_b(r, c, image_bytes)))
                elif row_filter == 3:
                    image_bytes.append(0xff &
                                       int(decompressed_test[1 + c + (1 + width * color_type_bpp) * r] + (
                                                   recon_a(r, c, image_bytes)
                                                   + recon_b(r, c, image_bytes)) // 2))
                elif (row_filter == 4):
                    image_bytes.append(0xff & int(decompressed_test[1 + c + (1 + width * color_type_bpp) * r] +
                                                  paeth_predictor(recon_a(r, c, image_bytes),
                                                                  recon_b(r, c, image_bytes),
                                                                  recon_c(r, c, image_bytes))))

        # Applying palette
        if len(PLTE_data) > 0:
            depaleted = []
            for byte in image_bytes:
                depaleted.append(PLTE_data[byte * 3])
                depaleted.append(PLTE_data[byte * 3 + 1])
                depaleted.append(PLTE_data[byte * 3 + 2])
                if len(tRNS_data) > 0:
                    if len(tRNS_data) > byte:
                        depaleted.append(tRNS_data[byte])
                    else:
                        depaleted.append(255)

        # GRAYSCALE WITH NTSC FORMULA
        image_bytes_grayscale = []
        i = 0
        while i < len(image_bytes):
            if len(PLTE_data) > 0:
                if len(tRNS_data) > 0:
                    image_bytes_grayscale.append(
                        int((0.299 * depaleted[i * 4] + 0.587 * depaleted[i * 4 + 1] + 0.114 * depaleted[i * 4 + 2]) *
                            depaleted[i * 4 + 3] / 255 + (255 - depaleted[i * 4 + 3])))
                else:
                    image_bytes_grayscale.append(
                        int(0.299 * depaleted[i * 3] + 0.587 * depaleted[i * 3 + 1] + 0.114 * depaleted[i * 3 + 2]))
            elif color_type_bpp == 1:
                image_bytes_grayscale.append(int(image_bytes[i]))
            elif color_type_bpp == 2:
                image_bytes_grayscale.append(int(image_bytes[i] + (255 - image_bytes[i + 1])))
                # image_bytes_grayscale.append(int(image_bytes[i]))
                i += 1
            elif color_type_bpp == 3:
                image_bytes_grayscale.append(
                    int(0.299 * image_bytes[i] + 0.587 * image_bytes[i + 1] + 0.114 * image_bytes[i + 2]))
                i += 2
            elif color_type_bpp == 4:
                image_bytes_grayscale.append(
                    int((0.299 * image_bytes[i] + 0.587 * image_bytes[i + 1] + 0.114 * image_bytes[i + 2]) *
                        image_bytes[i + 3] / 255 + (255 - image_bytes[i + 3])))
                # image_bytes_grayscale.append(int((0.299 * image_bytes[i] + 0.587 * image_bytes[i + 1] + 0.114 * image_bytes[i + 2])))
                i += 3
            i += 1

        plt.figure(1)

        plt.subplot(131)
        plt.imshow(np.array(image_bytes_grayscale).reshape((height, width)), cmap='gray', vmin=0, vmax=255)
        plt.title('Image in grayscale'), plt.xticks([]), plt.yticks([])

        fourier = np.fft.fft2(np.array(image_bytes_grayscale).reshape((height, width)))
        fourier_shifted = np.fft.fftshift(fourier)
        fourier_mag = np.asarray(20 * np.log10(np.abs(fourier_shifted)), dtype=np.uint8)
        fourier_phase = np.asarray(np.angle(fourier_shifted), dtype=np.uint8)

        plt.subplot(132)
        plt.imshow(fourier_mag, cmap='gray')
        plt.title('FFT Magnitude'), plt.xticks([]), plt.yticks([])

        plt.subplot(133)
        plt.imshow(fourier_phase, cmap='gray')
        plt.title('FFT Phase'), plt.xticks([]), plt.yticks([])

        plt.figure(2)

        plt.subplot(121)
        fourier_inverted = np.fft.ifft2(fourier)
        plt.imshow(np.asarray(fourier_inverted.real, dtype=np.uint8), cmap='gray')
        plt.title('Image after inverted fft'), plt.xticks([]), plt.yticks([])

        difference = np.subtract(np.array(image_bytes_grayscale).reshape((height, width)), fourier_inverted)
        difference = np.abs(difference)
        plt.subplot(122)
        plt.imshow(np.asarray(difference.real, dtype=np.uint8), cmap='gray')
        plt.title('Difference'), plt.xticks([]), plt.yticks([])

        print("\nMax difference between image in grayscale and the same image\n"
              "after FFT and inverted FFT:")
        print(np.max(difference))

        if len(PLTE_data) > 0:
            palette_with_trans = []
            for i in range(len(PLTE_data)):
                if i < len(tRNS_data) * 3:
                    palette_with_trans.append(
                        int(PLTE_data[i] * tRNS_data[int(i / 3)] / 255 + (255 - tRNS_data[int(i / 3)])))
                else:
                    palette_with_trans.append(PLTE_data[i])
            while len(palette_with_trans) < 256 * 3:
                palette_with_trans.append(0)
            plt.figure(3)
            plt.imshow(np.array(palette_with_trans).reshape((16, 16, 3)), vmin=0, vmax=255)
            plt.title('Palette'), plt.xticks([]), plt.yticks([])

        # plt.imshow(np.array(depaleted).reshape((height, width, color_type_bpp)), cmap='gray', vmin=0, vmax=255)
        plt.show()



# Nazwy plików do najlepszego przetestowania odpowiednich funckjonalności
# itxt - iTXt_test, itxt_not_XMP
# PLTE - PLTE, PLTE_test
# Fourier - 1

#image_name = 'dragon'
#chunks = get_chunks(image_name)
#analyze_chunks(chunks)
#save_anonymized(chunks)



# Wyświetlanie obrazu
# image_display = Image.open(image_name + '.png')
# image_display.show()

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
