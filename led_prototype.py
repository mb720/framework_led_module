#!/bin/python
NR_OF_COLUMNS = 9
NR_OF_ROWS = 34
MAX_BRIGHTNESS = 255


def main():
    print("Start of program")
    args = get_commandline_args()
    Argparse requires the --device and brightness-matrix arguments to be provided on the command line
    devices = args.device
    matrix = matrix_from_string(args.brightness_matrix)
    print("Brightness matrix from input string, pretty printed:")
    pretty_print_matrix(matrix)

    for device in devices:
        draw_brightness_matrix(device, matrix)

    print("End of program")


def draw_brightness_matrix(dev, matrix):
    """Draw the brightness matrix on the LED module."""
    for col_index in range(0, NR_OF_COLUMNS):
        stage_col(dev, col_index, get_column(matrix, col_index))
    commit_cols(dev)


def get_column(matrix, col_index):
    nr_of_rows = len(matrix)
    return [matrix[row][col_index] for row in range(nr_of_rows)]


def stage_col(dev, column_index, vals):
    """Stage brightness values for a single column. Must be committed later with commit_cols()."""
    stage_col_brightness_values_cmd = 0x07
    send_command(dev, stage_col_brightness_values_cmd, [column_index] + vals)


def commit_cols(dev):
    """Commit the changes from sending individual cols with stage_col(), displaying the brightness values on the LED module."""
    draw_col_brightness_values = 0x08
    send_command(dev, draw_col_brightness_values, [0x00])


def matrix_from_string(matrix_as_string):
    """Convert the matrix given as a string to a two-dimensional list.

    Example matrix as a string: "[100,33,100,33,100,33,100,33,100],[100,32,100,32,100,32,100,32,100]" and so forth.

    The first row in the matrix is the top row on the LED display."""
    return [
        [int(value) for value in row.split(",")]
        for row in matrix_as_string[1:-1].split("],[")
    ]


def matrix_to_string(matrix):
    """Convert the matrix to a string that separates bracket-delimited rows with a comma. See matrix_from_string for example strings specifying the matrix."""
    return "[" + "],[".join([",".join(map(str, row)) for row in matrix]) + "]"


def pretty_print_matrix(matrix):
    """Print the matrix to stdout using spaces as delimiters for the columns and line breaks for the rows. Pad wow values with leading spaces to 3 characters."""
    for row in matrix:
        row_as_string = " ".join([str(value).rjust(3) for value in row])
        print(row_as_string)


def create_test_brightness_matrix():
    """Create a two-dimensional list (34 rows and 9 columns) containing brightness values from 0 to 255"""
    matrix = [[0 for x in range(NR_OF_COLUMNS)] for y in range(NR_OF_ROWS)]

    val = 0
    for row in range(NR_OF_ROWS):
        for col in range(NR_OF_COLUMNS):
            matrix[row][col] = val
            val = (val + 1) % (MAX_BRIGHTNESS + 1)

    return matrix


def send_draw_command(dev, bytes):
    """Send a draw command to the LED module that turns LEDs on or off.

    The draw command (0x06) requires 39 bytes to be sent to the module. With a 34x9 matrix, we need 34*9 = 306 bits to represent the individual LED's state (on or off). 306 bits fit into 39 bytes: 306/8 = 38.25.

    The bits in those bytes represent the state of the individual LEDs on the module. The first bit represents the top left LED, the second bit the LED to the right of it, and so forth. The 10th bit represents the LED in the second row, first column, and so forth.
    """
    draw_cmd_byte = 0x06
    send_command(dev, draw_cmd_byte, bytes)


def send_command(dev, command, parameters=[], with_response=False):
    """Send a command to the device. Opens a new serial connection every time."""
    # https://github.com/FrameworkComputer/inputmodule-rs/blob/ad3a034b9fe08cf662e57ee013a6b4e9afe75fd2/python/inputmodule/inputmodule/__init__.py#L7
    fwk_magic = [0x32, 0xAC]
    return send_command_raw(dev, fwk_magic + [command] + parameters, with_response)


def send_command_raw(dev, command, with_response=False):
    import serial

    """Send a command to the device. Opens a new serial connection every time."""
    try:
        with serial.Serial(dev, 115200) as s:
            s.write(command)

            # Response size from here:
            # https://github.com/FrameworkComputer/inputmodule-rs/blob/ad3a034b9fe08cf662e57ee013a6b4e9afe75fd2/python/inputmodule/inputmodule/__init__.py#L90
            # https://github.com/FrameworkComputer/inputmodule-rs/blob/main/commands.md

            response_size = 32
            if with_response:
                res = s.read(response_size)
                print(f"Received: {res}")
                return res
    except (IOError, OSError) as _ex:
        disconnect_dev(dev.device)
        print("Error: ", ex)


def get_commandline_args():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--brightness-matrix",
        required=True,
        help='brightness matrix as string. The string specifies a matrix with 9 columns and 34 rows where each row is delimited by brackets, and separated by commas. Three rows for example: "[100,33,100,33,100,33,100,33,100],[100,32,100,32,100,32,100,32,100],[100,31,100,31,100,31,100,31,100], ...". The first row in the matrix is the top row on the LED display.',
    )

    parser.add_argument(
        "--device",
        action="extend",
        nargs=1,
        required=True,
        help="LED device to use. Can be specified multiple times. Example: --device /dev/ttyACM0 --device /dev/ttyACM1",
    )

    return parser.parse_args()

def black_white_draw_test(dev):
    matrix = [[0 for col in range(NR_OF_COLUMNS)] for row in range(NR_OF_ROWS)]

    for row in range(NR_OF_ROWS):
        for col in range(NR_OF_COLUMNS):
            # Columns with even index are on, others are off
            val = 1 if col % 2 == 0 else 0
            matrix[row][col] = val

    print("Matrix to draw:")
    print(matrix)

    bytes_for_draw_cmd = matrix_to_bytes_for_black_white_draw_cmd(matrix)
    send_draw_command(dev, draw_cmd_byte, bytes_for_draw_cmd)


def matrix_to_bytes_for_black_white_draw_cmd(matrix):
    """Convert the 34x9 matrix consisting of 0s and 1s to bytes for the draw command (0x06) of the LED module.

    See send_draw_command for more information on how the bits in the bytes are used to represent the state of the LEDs.
    """
    bytes = [0x00 for _ in range(39)]

    for row in range(NR_OF_ROWS):
        for col in range(NR_OF_COLUMNS):
            # The index of the LED in the 34x9 matrix, starting from the top left corner
            led_index = col + NR_OF_COLUMNS * row
            if matrix[row][col]:
                byte_index = int(led_index / 8)
                bit_index = led_index % 8
                # Turning on bit at bit_index within the current byte
                bytes[byte_index] |= 1 << bit_index

    return bytes


def black_white_draw_pixels(dev):
    """ Use a list of 306 bits to draw a pattern of black and white pixels on the LED module."""

    # Each bit represents the state of an LED (1 is on, 0 is off)
    bits = [
            0, 0, 0, 0, 1, 0, 0, 0, 0,
            0, 0, 0, 1, 0, 1, 0, 0, 0,
            0, 0, 1, 0, 0, 0, 1, 0, 0,
            0, 1, 0, 0, 0, 0, 0, 1, 0,
            1, 0, 0, 0, 0, 0, 0, 0, 1,
            0, 1, 0, 0, 0, 0, 0, 1, 0,
            0, 0, 1, 0, 0, 0, 1, 0, 0,
            0, 0, 0, 1, 0, 1, 0, 0, 0,
            0, 0, 0, 0, 1, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0,

            0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0,

            0, 0, 0, 0, 1, 0, 0, 0, 0,
            0, 0, 0, 0, 1, 0, 0, 0, 0,
            0, 0, 0, 0, 1, 0, 0, 0, 0,
            0, 0, 0, 0, 1, 0, 0, 0, 0,
            1, 1, 1, 1, 1, 1, 1, 1, 1,
            0, 0, 0, 0, 1, 0, 0, 0, 0,
            0, 0, 0, 0, 1, 0, 0, 0, 0,
            0, 0, 0, 0, 1, 0, 0, 0, 0,
            0, 0, 0, 0, 1, 0, 0, 0, 0,
            0, 0, 0, 0, 1, 0, 0, 0, 0,

            0, 0, 0, 0, 0, 0, 0, 0, 0,
            1, 0, 0, 0, 0, 0, 0, 0, 1,
            0, 1, 0, 0, 0, 0, 0, 1, 0,
            0, 0, 1, 0, 0, 0, 1, 0, 0,
            0, 0, 0, 1, 0, 1, 0, 0, 0,
            0, 0, 0, 0, 1, 0, 0, 0, 0,
            0, 0, 0, 1, 0, 1, 0, 0, 0,
            0, 0, 1, 0, 0, 0, 1, 0, 0,
            0, 1, 0, 0, 0, 0, 0, 1, 0,
            1, 0, 0, 0, 0, 0, 0, 0, 1,

            0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0
           ]

    bytes = bits_to_bytes(bits)
    send_draw_command(dev, bytes)

def bits_to_bytes(bits):
    """Convert a list of bits to a list of bytes."""
    import math
    nr_of_bytes = math.ceil(len(bits) / 8)
    bytes = [0x00 for _ in range(nr_of_bytes)]

    for bit_index, bit in enumerate(bits):
        byte_index = int(bit_index / 8)
        bit_index_within_byte = bit_index % 8
        if bit:
            # Set the byte's bit to one at bit_index_within_byte
            bytes[byte_index] |= 1 << bit_index_within_byte

    return bytes


if __name__ == "__main__":
    main()
