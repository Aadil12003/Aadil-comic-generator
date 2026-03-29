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

# ==========================================
# 2. SESSION STATE MANAGEMENT
# ==========================================
if 'comic_ready' not in st.session_state:
    st.session_state.comic_ready = False
if 'final_images' not in st.session_state:
    st.session_state.final_images = []
if 'script_data' not in st.session_state:
    st.session_state.script_data = []
if 'pdf_bytes' not in st.session_state:
    st.session_state.pdf_bytes = None
if 'gif_bytes' not in st.session_state:
    st.session_state.gif_bytes = None

# ==========================================
# 3. SIDEBAR (TOOLS & SETTINGS)
# ==========================================
with st.sidebar:
    st.header("🛠️ Director's Tools")
    
    if not API_KEY:
        st.error("⚠️ NVIDIA_API_KEY is missing!")
    
    num_panels = st.number_input("Number of Panels", min_value=1, value=4, step=1)
    
    st.markdown("### 🎨 Art Direction")
    art_style = st.selectbox(
        "Comic Style", 
        ["Modern American Comic (Marvel/DC)", "Classic Vintage Comic", "Japanese Manga (Black & White)", "Dark Noir Graphic Novel", "Vibrant Cyberpunk", "Watercolor Storybook"]
    )
    
    st.markdown("### 🖼️ Character Reference (Optional)")
    reference_image = st.file_uploader("Upload a face for guidance (or leave blank for AI choice)", type=['png', 'jpg', 'jpeg'])

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
            raise Exception(f"API Error: {e}")

def add_comic_caption(img, text):
    """Pro lettering using your uploaded Bangers-Regular.ttf file."""
    width, height = img.size
    
    # Font Loading Logic
    font_size = 48
    try:
        font = ImageFont.truetype("Bangers-Regular.ttf", font_size)
    except IOError:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
        except:
            font = ImageFont.load_default()

    wrapped_text = textwrap.fill(text, width=40)
    
    # Calculate box height
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), wrapped_text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    caption_height = text_height + 80
    new_img = Image.new('RGB', (width, height + caption_height), '#FFFBEB')
    new_img.paste(img, (0, 0))
    
    draw = ImageDraw.Draw(new_img)
    draw.line([(0, height), (width, height)], fill="black", width=8)
    
    # Centering text
    tx = (width - text_width) / 2
    ty = height + (caption_height - text_height) / 2 - 10
    draw.multiline_text((tx, ty), wrapped_text, fill="black", font=font, align="center")
    
    return new_img

def generate_comic_script(idea, style, panels):
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = f"""
    You are a comic writer. Create a {panels}-panel story.
    RULES:
    1. Short captions (max 15 words).
    2. image_prompts must use strict visual tags for consistency (e.g. 'blonde hair, red cape').
    3. Output ONLY a JSON array [{{...}}].
    """
    
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Comic idea: {idea} in {style} style"}
        ],
        "temperature": 0.3
    }
    
    res = fetch_from_api_with_retry(url, headers, payload)
    raw = res.json()["choices"][0]["message"]["content"]
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    return json.loads(match.group(0))

def generate_image(prompt, seed, init_image_b64=None):
    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 7,
        "seed": seed,
        "steps": 30
    }
    
    # If we have an anchor image, use it for consistency
    if init_image_b64:
        payload["init_image"] = init_image_b64
        payload["image_strength"] = 0.5 # Balance between new action and old face
    
    res = fetch_from_api_with_retry(url, headers, payload)
    b64 = res.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64))), b64

# ==========================================
# 5. MAIN DASHBOARD
# ==========================================
st.title("📓 Pro AI Comic Studio")

user_idea = st.text_area("📖 Story Idea", "A cute blue owl learning to fly in a dark forest.", height=100)

if st.button("🚀 Produce My Comic", use_container_width=True, type="primary"):
    if not API_KEY:
        st.error("Missing API Key!")
    else:
        try:
            shared_seed = int(time.time()) % 1000000
            
            with st.status("🎬 Production in progress...", expanded=True) as status:
                script = generate_comic_script(user_idea, art_style, num_panels)
                
                # Setup initial anchor image (if user provided one)
                anchor_b64 = None
                if reference_image:
                    anchor_b64 = base64.b64encode(reference_image.getvalue()).decode('utf-8')
                
                final_panels = []
                for i, scene in enumerate(script):
                    status.update(label=f"🖌️ Drawing Panel {i+1}...")
                    
                    # Generate the image
                    img, current_b64 = generate_image(scene["image_prompt"], shared_seed, anchor_b64)
                    
                    # If user didn't provide an image, Panel 1 becomes the anchor for Panel 2, 3, 4
                    if i == 0 and not reference_image:
                        anchor_b64 = current_b64
                    
                    # Lettering
                    lettered_img = add_comic_caption(img, scene["caption"])
                    final_panels.append(lettered_img)
                
                st.session_state.final_images = final_panels
                st.session_state.comic_ready = True
                status.update(label="🎉 Done!", state="complete")

        except Exception as e:
            st.error(f"Error: {e}")

# Display Results
if st.session_state.comic_ready:
    for img in st.session_state.final_images:
        st.image(img, use_container_width=True)
