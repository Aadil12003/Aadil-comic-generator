import streamlit as st
import requests
import base64
import json
import re
import time
from fpdf import FPDF
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ================= CONFIG =================
API_URL_TEXT = "https://integrate.api.nvidia.com/v1/chat/completions"
API_URL_IMAGE = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"

HEADERS = lambda key: {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

# ================= CHARACTER LOCK =================
CHARACTER_LOCK = {
    "aadil": "young indian man, black hair, short beard, sharp jawline, beige shirt",
    "angel": "young indian woman, long brown hair, blue saree, bindi, angel wings"
}

# ================= SAFE API CALL =================
def api_post(url, headers, payload):
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

# ================= SCRIPT GENERATION =================
def generate_script(api_key, idea, panels):
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [
            {
                "role": "system",
                "content": f"""
Create {panels} comic scenes.

Characters (DO NOT CHANGE):
Aadil: {CHARACTER_LOCK["aadil"]}
Angel: {CHARACTER_LOCK["angel"]}

Return ONLY JSON:
[
  {{
    "scene": "...",
    "labels": ["Age: 22", "Aadil: 24"]
  }}
]
"""
            },
            {"role": "user", "content": idea}
        ],
        "temperature": 0.3
    }

    data = api_post(API_URL_TEXT, HEADERS(api_key), payload)
    if not data:
        return []

    text = data["choices"][0]["message"]["content"]
    match = re.search(r'\[.*\]', text, re.DOTALL)

    return json.loads(match.group()) if match else []

# ================= PROMPT BUILDER =================
def build_prompt(scene, style):
    return f"""
{style}, comic illustration, cinematic lighting

Character Aadil: {CHARACTER_LOCK["aadil"]}
Character Angel: {CHARACTER_LOCK["angel"]}

STRICT RULES:
- same face
- same clothes
- same character design

Scene: {scene}

high detail, consistent character, professional comic art
"""

# ================= IMAGE GENERATION =================
def generate_image(api_key, prompt, seed):
    payload = {
        "text_prompts": [
            {"text": prompt, "weight": 1},
            {"text": "different face, mutation, distortion, inconsistent character", "weight": -1}
        ],
        "cfg_scale": 9,
        "seed": seed,
        "steps": 30
    }

    data = api_post(API_URL_IMAGE, {"Authorization": f"Bearer {api_key}"}, payload)
    if not data:
        return None

    img_b64 = data["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(img_b64)))

# ================= TEXT OVERLAY =================
def add_labels(img, labels):
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except:
        font = ImageFont.load_default()

    y = 20
    for label in labels:
        draw.text((20, y), label, fill="white", font=font)
        y += 40

    return img

# ================= MAIN =================
st.title("🎬 Pro Comic Generator (Enhanced)")

api_key = st.text_input("API Key", type="password")

idea = st.text_area("Story Idea")

panels = st.slider("Panels", 1, 10, 4)

style = st.selectbox("Style", [
    "cinematic comic",
    "anime style",
    "pixar style",
    "dark noir"
])

if st.button("Generate"):

    if not api_key:
        st.warning("Enter API key")
        st.stop()

    seed = 123456  # fixed seed for consistency

    with st.spinner("Generating story..."):
        script = generate_script(api_key, idea, panels)

    images = []

    for i, scene in enumerate(script):
        st.write(f"Generating Panel {i+1}")

        prompt = build_prompt(scene["scene"], style)

        img = generate_image(api_key, prompt, seed)

        if img:
            img = add_labels(img, scene.get("labels", []))
            images.append(img)
            st.image(img)
