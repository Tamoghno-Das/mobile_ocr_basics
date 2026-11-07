from io import BytesIO
import os

from PIL import Image, ImageOps, UnidentifiedImageError
import requests
import streamlit as st


def extract_text(photo):
    with Image.open(photo) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((1600, 1600))

        with BytesIO() as buffer:
            image.save(buffer, format="JPEG", quality=80)
            image_bytes = buffer.getvalue()

    response = requests.post(
        "https://api.ocr.space/parse/image",
        headers={"apikey": os.getenv("OCR_API_KEY", "helloworld")},
        files={"file": ("scan.jpg", image_bytes, "image/jpeg")},
        data={"language": "eng", "OCREngine": "2"},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if result.get("IsErroredOnProcessing"):
        messages = result.get("ErrorMessage")
        if isinstance(messages, list):
            messages = " ".join(messages)
        raise ValueError(messages or "The OCR service could not read this image.")

    return "\n".join(
        page.get("ParsedText", "") for page in result.get("ParsedResults") or []
    ).strip()


st.set_page_config(page_title="Phone OCR Scanner")
st.title("Phone OCR Scanner")
st.write("Take a clear photo of printed English text or upload one.")

source = st.radio("Image source", ["Camera", "Gallery"])

if source == "Camera":
    photo = st.camera_input("Take a photo")
else:
    photo = st.file_uploader("Choose a photo", type=["jpg", "jpeg", "png"])

if photo is not None and st.button("Extract text", type="primary"):
    st.session_state["scan_text"] = ""

    try:
        with st.spinner("Reading the image…"):
            st.session_state["scan_text"] = extract_text(photo)

        if not st.session_state["scan_text"]:
            st.info("No text found. Try a closer photo in brighter light.")
    except (UnidentifiedImageError, OSError):
        st.error("Could not open the photo. Try a different JPG or PNG.")
    except requests.RequestException:
        st.error("The OCR service could not complete the request. Try again.")
    except ValueError as error:
        st.error(str(error))

if st.session_state.get("scan_text"):
    text = st.text_area("Extracted text", key="scan_text", height=250)
    st.download_button("Download text", data=text, file_name="scan.txt")
    