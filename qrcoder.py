import sys
import os
import argparse
import qrcode
from PIL import Image, UnidentifiedImageError

# Default directory where generated QR Codes are saved. It is created on demand
# and is meant to be ignored by Git.
OUTPUT_DIR = "output"


def generate_qrcode(link: str, logo_path: str | None = None, output_path: str = "qrcode.png") -> str:
    """
    Generate a QR Code encoding `link` and write it to `output_path`.
    If `logo_path` is provided and points to a valid image, insert the
    logo centered. If the logo is missing or invalid, emit a warning and
    generate the QR Code without the logo.
    Return the path of the written output file.
    Raise an I/O exception if writing fails.
    """
    qr = qrcode.QRCode(
        version=4,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    qr.add_data(link)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Optional logo insertion in the center, with graceful degradation.
    if logo_path:
        if not os.path.exists(logo_path):
            print(
                f"WARNING: logo file {logo_path!r} was not found. "
                "Generating without logo..."
            )
        else:
            try:
                logo = Image.open(logo_path)
                logo.load()
            except (UnidentifiedImageError, OSError):
                print(
                    f"WARNING: logo file {logo_path!r} is not a valid image. "
                    "Generating without logo..."
                )
            else:
                qr_width, qr_height = qr_img.size
                logo_size = qr_width // 4
                # Resize proportionally, never exceeding 1/4 of the QR width.
                logo.thumbnail((logo_size, logo_size))

                logo_x = (qr_width - logo.size[0]) // 2
                logo_y = (qr_height - logo.size[1]) // 2

                qr_img.paste(
                    logo,
                    (logo_x, logo_y),
                    mask=logo if logo.mode == "RGBA" else None,
                )

    # Write with I/O failure handling, leaving no partial file behind.
    try:
        # Create the parent directory on demand (e.g. the default output/ dir).
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        qr_img.save(output_path)
    except OSError as error:
        # Remove any partial file left by the write attempt.
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        raise OSError(
            f"Error writing the output file {output_path!r}: {error}."
        ) from error

    print(f"QR Code generated: {output_path}")
    return output_path


def validate_link(link: str, max_chars: int = 2953) -> None:
    """
    Validate the `link` to be encoded in the QR Code.
    Raise `ValueError` if the link is empty, whitespace-only, or exceeds
    `max_chars` characters. Otherwise return None (link accepted).
    """
    if not link or not link.strip():
        raise ValueError(
            "Error: the provided link is invalid (empty or whitespace only)."
        )

    if len(link) > max_chars:
        raise ValueError(
            "Error: the link exceeds the limit of 2,953 characters."
        )

    return None


def resolve_output_path(logo_path: str | None, output_arg: str | None) -> str:
    """
    Resolve the output file path.
    Return `output_arg` unchanged when provided (the user chooses the exact
    path). Otherwise derive a default name inside OUTPUT_DIR: "qrcode_with_logo.png"
    when there is a logo and "qrcode_simple.png" when there is none.
    """
    if output_arg:
        return output_arg

    default_name = "qrcode_with_logo.png" if logo_path else "qrcode_simple.png"
    return os.path.join(OUTPUT_DIR, default_name)


def build_parser() -> argparse.ArgumentParser:
    """
    Create and configure the CLI ArgumentParser, with description and help
    texts in English.

    Defines:
    - `link`: required positional argument (the link to encode).
    - `--logo`/`-l`: optional path to the logo image.
    - `--output`/`-o`: optional path to the output PNG file.
    """
    parser = argparse.ArgumentParser(
        prog="qrcoder",
        description=(
            "Generate a QR Code image from a link, with the option to insert "
            "a logo in the center."
        ),
        epilog=(
            "Without a logo, the default file is 'qrcode_simple.png'; with a "
            "logo, 'qrcode_with_logo.png'."
        ),
    )

    parser.add_argument(
        "link",
        help=(
            "The link (URL) to encode in the QR Code "
            "(required, maximum of 2,953 characters)."
        ),
    )

    parser.add_argument(
        "-l",
        "--logo",
        dest="logo",
        default=None,
        help="Path to the logo image file to insert in the center (optional).",
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default=None,
        help=(
            "Path to the output PNG file (optional). When omitted, the name "
            "is derived automatically."
        ),
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Parse arguments, validate the link, resolve the output path, call
    `generate_qrcode`, and translate errors into messages with coherent
    exit codes.

    Return the exit code: 0 on success; non-zero on error (invalid link or
    write failure). For `-h`/`--help` and a missing link, argparse itself
    terminates the process (0 for help, non-zero when the required link is
    missing).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Validate the link before any generation work, avoiding partial files
    # on invalid input.
    try:
        validate_link(args.link)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    output_path = resolve_output_path(args.logo, args.output)

    try:
        generate_qrcode(args.link, logo_path=args.logo, output_path=output_path)
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

