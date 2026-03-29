import streamlit as st
import requests
import base64
import json
import re
import textwrap
import time
from fpdf import FPDF
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. STUDIO CONFIGURATION & SECRETS
# ==========================================
st.set_page_config(page_title="Pro AI Comic Studio", page_icon="📓", layout="wide")

try:
    API_KEY = st.secrets["NVIDIA_API_KEY"]
except Exception:
    API_KEY = None

st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #ffffff; }
    .stSidebar { background-color: #111827; }
    .panel-box { border: 1px solid #374151; padding: 15px; border-radius: 12px; background-color: #1f2937; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); margin-bottom: 20px; }
    h1, h2, h3 { color: #f87171; font-family: 'Arial Black', sans-serif; }
    </style>
""", unsafe_allow_html=True)

if 'comic_ready' not in st.session_state: st.session_state.comic_ready = False
if 'final_images' not in st.session_state: st.session_state.final_images = []

# ==========================================
# 3. SIDEBAR
# ==========================================
with st.sidebar:
    st.header("🛠️ Director's Tools")
    if not API_KEY: st.error("Missing NVIDIA_API_KEY in Secrets!")
    num_panels = st.number_input("Number of Panels", min_value=1, value=4, step=1)
    art_style = st.selectbox("Comic Style", ["Modern American Comic", "Classic Vintage", "Japanese Manga", "Dark Noir", "Vibrant Cyberpunk"])
    reference_image = st.file_uploader("Optional: Character Reference", type=['png', 'jpg', 'jpeg'])

# ==========================================
# 4. CORE AI FUNCTIONS
# ==========================================
def fetch_from_api_with_retry(url, headers, payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            raise Exception(f"Connection Error: {e}")

def add_comic_caption(img, text):
    """Pro lettering using your Bangers-Regular.ttf file."""
    width, height = img.size
    font_size = 48
    try:
        font = ImageFont.truetype("Bangers-Regular.ttf", font_size)
    except:
        try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
        except: font = ImageFont.load_default()

    wrapped_text = textwrap.fill(text, width=35)
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), wrapped_text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    
    cap_h = th + 80
    new_img = Image.new('RGB', (width, height + cap_h), '#FFFBEB')
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    draw.line([(0, height), (width, height)], fill="black", width=8)
    
    draw.multiline_text(((width-tw)/2, height + (cap_h-th)/2 - 10), wrapped_text, fill="black", font=font, align="center")
    return new_img

def generate_comic_script(idea, style, panels):
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = f"""
    Write a {panels}-panel comic. Return ONLY a JSON list.
    Rules: Short captions (15 words). Use visual tags for character consistency (e.g. 'blonde hair, red shirt').
    Structure: [ {{"caption": "...", "image_prompt": "..."}} ]
    """
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": idea}],
        "temperature": 0.3
    }
    
    res = fetch_from_api_with_retry(url, headers, payload)
    raw = res.json()["choices"][0]["message"]["content"]
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    return json.loads(match.group(0))

def generate_image(prompt, seed, init_b64=None):
    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 7, "seed": seed, "steps": 30
    }
    if init_b64:
        payload["init_image"] = init_b64
        payload["image_strength"] = 0.55 # Balance between face guidance and new scene
    
    res = fetch_from_api_with_retry(url, headers, payload)
    b64 = res.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64))), b64

# ==========================================
# 5. MAIN RENDER
# ==========================================
st.title("📓 Professional AI Comic Studio")
user_idea = st.text_area("📖 Story Idea", "A cute robot named Sparky learning to cook with a clumsy master chef.", height=100)

if st.button("🚀 Produce My Comic", use_container_width=True, type="primary"):
    try:
        shared_seed = int(time.time()) % 1000000
        with st.status("🎬 Production in progress...", expanded=True) as status:
            script = generate_comic_script(user_idea, art_style, num_panels)
            
            anchor_b64 = None
            if reference_image:
                anchor_b64 = base64.b64encode(reference_image.getvalue()).decode('utf-8')
            
            panels_out = []
            for i, scene in enumerate(script):
                # FIXED: Added fallback mapping for LLaMA's key name errors
                p_text = scene.get("image_prompt") or scene.get("prompt") or scene.get("visual") or "Comic scene"
                c_text = scene.get("caption") or scene.get("text") or ""
                
                status.update(label=f"🖌️ Drawing Panel {i+1}...")
                
                # Generate the visual from text
                img, curr_b64 = generate_image(p_text, shared_seed, anchor_b64)
                
                # If no image upload, the generated Panel 1 becomes the identity anchor
                if i == 0 and not reference_image:
                    anchor_b64 = curr_b64
                
                # Now add the lettered caption on top
                panels_out.append(add_comic_caption(img, c_text))
            
            st.session_state.final_images = panels_out
            st.session_state.comic_ready = True
            status.update(label="🎉 Production Complete!", state="complete")

    except Exception as e:
        st.error(f"Production Halted: {e}")

if st.session_state.comic_ready:
    for img in st.session_state.final_images:
        st.image(img, use_container_width=True)
