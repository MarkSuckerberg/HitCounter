from flask import Flask, send_file, request, redirect, url_for, render_template
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from io import BytesIO
from hitcount_file import HitCountBinary as HitCountFile
from typing import Optional, Literal, get_args

app = Flask(__name__)

FileType = Literal["webp", "gif", "png"]


@app.route("/")
def index():
    return render_template("base.html.j2")


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
@app.route("/count/<int:count>-<int:unique>.webp")
def counter(count: int, unique: Optional[int] = None, ext: FileType = "webp"):
    if ext not in get_args(FileType):
        return "Invalid file type", 400

    if unique:
        image = GenerateTickerUnique(count, unique, ext)
    else:
        image = GenerateTicker(count, ext)

    return send_file(image, f"image/{ext}")


@app.route("/ticker/<int:count>")
@app.route("/ticker/<int:count>.<ext>")
@app.route("/ticker/<int:count>-<int:unique>")
@app.route("/ticker/<int:count>-<int:unique>.<ext>")
def ticker(count: int, unique: Optional[int] = None, ext: FileType = "webp"):
    if ext not in get_args(FileType):
        return "Invalid file type", 400

    if unique:
        image = GenerateTickerUnique(count, unique, ext)
    else:
        image = GenerateAnimated(count, ext)
    return send_file(image, f"image/{ext}")


@app.route("/unique/counter")
@app.route("/unique/counter.<ext>")
def UniqueCount(ext: FileType = "webp"):
    count, unique = GetAndUpdateUnique(request.remote_addr)

    return redirect(url_for(counter.__name__, count=count, unique=unique, ext=ext))


@app.route("/counter")
@app.route("/counter.<ext>")
def CurrentCount():
    count = GetAndUpdateCount()

    return redirect(url_for(counter.__name__, count=count))


@app.route("/unique/ticker.webp")
def UniqueTicker():
    count, unique = GetAndUpdateUnique(request.remote_addr)

    return redirect(url_for(ticker.__name__, count=count, unique=unique))


@app.route("/ticker.webp")
def CurrentTicker():
    count = GetAndUpdateCount()

    return redirect(url_for(ticker.__name__, count=count))


def GenerateAnimated(count: int, fileType: FileType = "webp") -> BytesIO:
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
        fileType,
        save_all=True,
        append_images=generatedFrames[1:],
        disposal=2,
        lossless=True,
    )

    # Rewind so the file is sent from the beginning
    output.seek(0)
    return output


def GenerateTicker(count: int, fileType: FileType = "webp") -> BytesIO:
    with Image.open("bg.png") as bg:
        drawing = ImageDraw.Draw(bg)
        drawing.text(
            (0, 0), f"{count:010}", "red", ImageFont.load("font/seven-segment.pil")
        )
        del drawing

        output = BytesIO()
        bg.save(output, fileType, lossless=True)
        output.seek(0)

        return output


def GenerateTickerUnique(
    count: int, unique: int, fileType: FileType = "webp"
) -> BytesIO:
    with Image.open("bg-unique.png") as bg:
        uniqueBg = bg.copy()
        uniqueDrawing = ImageDraw.Draw(uniqueBg)
        uniqueDrawing.text(
            (0, 0), f"CD{unique:08}", "red", ImageFont.load("font/seven-segment.pil")
        )
        del uniqueDrawing

        drawing = ImageDraw.Draw(bg)
        drawing.text(
            (0, 0), f"AB{count:08}", "red", ImageFont.load("font/seven-segment.pil")
        )
        del drawing

        output = BytesIO()
        bg.save(
            output,
            fileType,
            save_all=True,
            append_images=[uniqueBg],
            disposal=2,
            duration=5000,
            lossless=True,
        )
        output.seek(0)

        return output


if __name__ == "__main__":
    app.run()
