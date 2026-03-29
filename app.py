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

# Professional Dark UI
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #ffffff; }
    .stSidebar { background-color: #111827; }
    .panel-box { border: 2px solid #374151; padding: 10px; border-radius: 8px; background-color: #1f2937; margin-bottom: 20px; }
    h1, h2, h3 { color: #f87171; font-family: 'Arial Black', sans-serif; }
    </style>
""", unsafe_allow_html=True)

if 'comic_ready' not in st.session_state: st.session_state.comic_ready = False
if 'final_images' not in st.session_state: st.session_state.final_images = []
if 'pdf_bytes' not in st.session_state: st.session_state.pdf_bytes = None

# ==========================================
# 2. SIDEBAR TOOLS & ART PRESETS
# ==========================================
with st.sidebar:
    st.header("🛠️ Director's Tools")
    if not API_KEY: st.error("⚠️ NVIDIA_API_KEY is missing!")
    
    num_panels = st.number_input("Number of Panels", min_value=1, value=4, step=1)
    
    art_choice = st.selectbox("Art Style Preset", [
        "Modern Superhero (Marvel/DC)", 
        "Studio Ghibli Anime", 
        "3D Disney/Pixar Style",
        "Cyberpunk Neon", 
        "Dark Noir (B&W)", 
        "Vintage 1950s Newsprint", 
        "Rough Pencil Sketch"
    ])
    
    style_map = {
        "Modern Superhero (Marvel/DC)": "highly detailed comic book art, sharp inks, vibrant colors, heroic lighting",
        "Studio Ghibli Anime": "hand-drawn anime style, lush landscapes, soft lighting, whimsical, Ghibli inspired",
        "3D Disney/Pixar Style": "octane render, 3D animation style, cute proportions, soft shadows, high definition",
        "Cyberpunk Neon": "futuristic digital art, glowing neon lights, high contrast, synthwave colors",
        "Dark Noir (B&W)": "monochrome, heavy shadows, film noir, gritty ink wash, high contrast black and white",
        "Vintage 1950s Newsprint": "retro comic book style, ben-day dots, aged paper texture, 1950s aesthetic",
        "Rough Pencil Sketch": "hand-drawn graphite sketch, messy lines, artistic, hatching"
    }
    
    st.markdown("---")
    if st.button("🔄 Clear & Start New"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# ==========================================
# 3. CORE AI FUNCTIONS
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
    
    cap_h = th + 90
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
    Rules: Short captions (15 words).
    CRITICAL: Describe the character's clothing and hair identically in every panel.
    Structure: [ {{"caption": "...", "image_prompt": "..."}} ]
    """
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": idea}],
        "temperature": 0.4
    }
    
    res = fetch_from_api_with_retry(url, headers, payload)
    raw = res.json()["choices"][0]["message"]["content"]
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    return json.loads(match.group(0))

def generate_image(prompt, seed):
    """Fixed Text-to-Image call using shared seed for character consistency."""
    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 8, 
        "seed": seed, # Shared seed locks character identity
        "steps": 30
    }
    
    res = fetch_from_api_with_retry(url, headers, payload)
    b64 = res.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64)))

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
st.title("📓 Professional AI Comic Studio")
user_idea = st.text_area("📖 What is the story about?", "A rogue astronaut finds an ancient library on a dead moon.", height=100)

if st.button("🚀 Produce My Comic", use_container_width=True, type="primary"):
    try:
        shared_seed = int(time.time()) % 1000000
        style_tags = style_map[art_choice]
        
        with st.status(f"🎬 Creating your {art_choice} comic...", expanded=True) as status:
            script = generate_comic_script(user_idea, art_choice, num_panels)
            
            panels_out = []
            for i, scene in enumerate(script):
                full_prompt = f"{style_tags}, " + (scene.get("image_prompt") or "Comic scene")
                c_text = scene.get("caption") or ""
                
                status.update(label=f"🖌️ Drawing Panel {i+1} of {len(script)}...")
                img = generate_image(full_prompt, shared_seed)
                panels_out.append(add_comic_caption(img, c_text))
            
            st.session_state.final_images = panels_out
            
            # Create PDF
            pdf = FPDF()
            for p in panels_out:
                pdf.add_page()
                buf = BytesIO()
                p.save(buf, format="PNG")
                pdf.image(buf, x=10, y=10, w=190)
            
            # FIXED: Explicitly convert bytearray to raw bytes for Streamlit
            st.session_state.pdf_bytes = bytes(pdf.output())
            
            st.session_state.comic_ready = True
            status.update(label="🎉 Production Complete!", state="complete")

    except Exception as e:
        st.error(f"Production Halted: {e}")

# Display Section
if st.session_state.comic_ready:
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📄 Download PDF Book",
            data=st.session_state.pdf_bytes,
            file_name="my_comic_book.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col2:
        gif_buf = BytesIO()
        st.session_state.final_images[0].save(gif_buf, format="GIF", save_all=True, append_images=st.session_state.final_images[1:], duration=2000, loop=0)
        st.download_button("🎞️ Download GIF Preview", gif_buf.getvalue(), "my_comic.gif", "image/gif", use_container_width=True)

    st.markdown("---")
    cols = st.columns(2)
    for idx, img in enumerate(st.session_state.final_images):
        with cols[idx % 2]:
            st.markdown(f"<div class='panel-box'>", unsafe_allow_html=True)
            st.image(img, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
