from flask import Flask, send_file
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from io import BytesIO
import fcntl
from multiprocessing import Process
from json import dump
from os import getenv

BYTE_COUNT = 4

app = Flask(__name__)

try:
    with open(f"data/hitcount.dat", "xb") as new_file:
        fcntl.flock(new_file, fcntl.LOCK_EX)

        initial_value = int(getenv("INITIAL_COUNT") or 0)
        new_file.write(initial_value.to_bytes(BYTE_COUNT))

        fcntl.flock(new_file, fcntl.LOCK_UN)
except FileExistsError:
    pass


@app.route("/")
def index():
    return """<html>
<body>
<img src='/counter.webp' style='background-color: black'></img>
<img src='/ticker.webp' style='background-color: black'></img>
</body>
</html>
"""


@app.route("/counter.webp")
def count():
    image = generate_animated(get_count())
    return send_file(image, "image/webp")


@app.route("/ticker.webp")
def ticker():
    image = generate_ticker(get_count())
    return send_file(image, "image/webp")


def update_json(count: int):
    with open("data/hitcount.json", "w") as json:
        fcntl.flock(json, fcntl.LOCK_EX)
        dump(count, json)
        fcntl.flock(json, fcntl.LOCK_UN)


def get_count() -> int:
    count: int = 0
    with open("data/hitcount.dat", "r+b") as count_file:
        # Lock so only we can read + update the file
        fcntl.flock(count_file, fcntl.LOCK_EX)

        # Read the saved hitcount
        count = int.from_bytes(count_file.read(BYTE_COUNT))
        count += 1

        # Overwrite the saved hitcount
        count_file.seek(0)
        count_file.write(count.to_bytes(BYTE_COUNT))

        fcntl.flock(count_file, fcntl.LOCK_UN)

    # Update the JSON save in the background, since it's not actually important functionally
    Process(target=update_json, args=(count,)).start()
    return count


def generate_animated(count: int) -> BytesIO:
    # Loop through all the frames, adding the text to each frame, before stitching them all back together
    generated_frames: list[Image.Image] = []

    with Image.open("animated.gif") as img:
        for frame in ImageSequence.Iterator(img):
            drawing = ImageDraw.Draw(frame)
            drawing.text(
                (0, 0),
                f"{count:08}",
                "red",
                ImageFont.load_default_imagefont(),
            )
            del drawing

            generated_frames.append(frame.copy())

    # Write to memory so we don't have to save it as a file and then immediately re-read it
    output = BytesIO()
    generated_frames[0].save(
        output,
        "WEBP",
        save_all=True,
        append_images=generated_frames[1:],
        disposal=2,
        lossless=True,
    )

    # Rewind so the file is sent from the beginning
    output.seek(0)
    return output


def generate_ticker(count: int) -> BytesIO:
    with Image.open("bg.png") as bg:
        drawing = ImageDraw.Draw(bg)
        drawing.text(
            (0, 0), f"{count:08}", "red", ImageFont.load("font/seven-segment.pil")
        )
        del drawing

        output = BytesIO()
        bg.save(output, "WEBP", lossless=True)
        output.seek(0)

        return output
