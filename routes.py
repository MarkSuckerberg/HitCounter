from flask import Flask, send_file, request, redirect
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from io import BytesIO
from hitcount_file import HitCountJson as HitCountFile

app = Flask(__name__)


@app.route("/")
def index():
    return """<html>
<body>
<img src='/counter.webp' style='background-color: black'></img>
<img src='/ticker.webp' style='background-color: black'></img>
</body>
</html>
"""


def GetAndUpdateUnique(visitor: str) -> tuple[int, int]:
    with HitCountFile("data/hitcount.dat") as data:
        data.NewVisitor(visitor)
        return (data.count, data.unique)


def GetAndUpdateCount():
    with HitCountFile("data/hitcount.dat") as data:
        data.count += 1
        return data.count


@app.route("/data.json")
def data():
    with HitCountFile("data/hitcount.dat") as data:
        return {
            "Count": data.count,
            "Unique": data.unique,
        }


@app.route("/count/<int:count>.webp")
def count(count):
    image = GenerateAnimated(count)
    return send_file(image, "image/webp")


@app.route("/ticker/<int:count>.webp")
def ticker(count):
    image = GenerateTicker(count)
    return send_file(image, "image/webp")


@app.route("/counter.webp")
def CurrentCount():
    count, unique = GetAndUpdateUnique(request.remote_addr)

    return redirect(f"/count/{count}.webp")


@app.route("/ticker.webp")
def CurrentTicker():
    count, unique = GetAndUpdateUnique(request.remote_addr)

    return redirect(f"/ticker/{unique}.webp")


def GenerateAnimated(count: int) -> BytesIO:
    # Loop through all the frames, adding the text to each frame, before stitching them all back together
    generatedFrames: list[Image.Image] = []

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

            generatedFrames.append(frame.copy())

    # Write to memory so we don't have to save it as a file and then immediately re-read it
    output = BytesIO()
    generatedFrames[0].save(
        output,
        "WEBP",
        save_all=True,
        append_images=generatedFrames[1:],
        disposal=2,
        lossless=True,
    )

    # Rewind so the file is sent from the beginning
    output.seek(0)
    return output


def GenerateTicker(count: int) -> BytesIO:
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


if __name__ == "__main__":
    app.run()
