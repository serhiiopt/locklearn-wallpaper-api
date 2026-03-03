from io import BytesIO

from fastapi import FastAPI, Response

from your_script import create_wallpaper

app = FastAPI()


@app.get("/generate")
async def generate_api(word: str, meaning: str):
    """
    Generate a wallpaper for a single word and its meaning.
    Returns a PNG image.
    """
    img = create_wallpaper(word, meaning)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")

