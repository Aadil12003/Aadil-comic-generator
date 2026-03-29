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

# Custom Dark Mode Styling
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
if 'gif_bytes' not in st.session_state: st.session_state.gif_bytes = None

# ==========================================
# 2. SIDEBAR TOOLS
# ==========================================
with st.sidebar:
    st.header("🛠️ Director's Tools")
    if not API_KEY: st.error("⚠️ NVIDIA_API_KEY is missing!")
    
    num_panels = st.number_input("Number of Panels", min_value=1, value=4, step=1)
    art_choice = st.selectbox("Art Style Preset", ["Modern Superhero", "Studio Ghibli Anime", "3D Pixar Style", "Dark Noir"])
    
    style_map = {
        "Modern Superhero": "highly detailed comic book art, sharp inks, vibrant colors",
        "Studio Ghibli Anime": "hand-drawn anime style, soft lighting, whimsical",
        "3D Pixar Style": "3D animation style, cute proportions, soft shadows, 8k",
        "Dark Noir": "monochrome, heavy shadows, film noir, gritty ink"
    }
    
    st.markdown("---")
    st.info("💡 **Consistency Mode:** Character DNA and environment are locked across all panels.")
    
    if st.button("🔄 Clear & Start New Story"):
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
            raise Exception(f"API Error: {e}")

def add_comic_caption(img, text):
    """Pro lettering with dynamic height."""
    width, height = img.size
    try:
        font = ImageFont.truetype("Bangers-Regular.ttf", 46)
    except:
        font = ImageFont.load_default()

    wrapped_text = textwrap.fill(text, width=40)
    draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = draw.textbbox((0, 0), wrapped_text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    
    cap_h = th + 90
    new_img = Image.new('RGB', (width, height + cap_h), '#FFFBEB')
    new_img.paste(img, (0, 0))
    d = ImageDraw.Draw(new_img)
    d.line([(0, height), (width, height)], fill="black", width=8)
    d.multiline_text(((width-tw)/2, height + (cap_h-th)/2 - 10), wrapped_text, fill="black", font=font, align="center")
    return new_img

def generate_comic_script(idea, style, panels):
    """UPGRADED: Narrative writer that enforces matching imagery."""
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = f"""
    You are a professional comic director. Create a {panels}-panel story.
    STRICT MATCHING RULES:
    1. Define a 'Visual Anchor' for the character (hair, clothes, distinct features).
    2. Every `image_prompt` MUST explicitly describe the action in the `caption`.
    3. Ensure the environment (background) is identical in every prompt.
    4. Return ONLY a JSON list: [ {{"caption": "...", "image_prompt": "..."}} ]
    """
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": idea}],
        "temperature": 0.2 # Lower temperature = stricter matching
    }
    
    res = fetch_from_api_with_retry(url, headers, payload)
    raw = res.json()["choices"][0]["message"]["content"]
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    return json.loads(match.group(0))

def generate_image(prompt, seed):
    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 9, # Slightly higher for better prompt adherence
        "seed": seed, 
        "steps": 30
    }
    res = fetch_from_api_with_retry(url, headers, payload)
    b64 = res.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64)))

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
st.title("📓 Professional AI Comic Studio")
user_idea = st.text_area("📖 Story Idea", "A small blue robot discovers a glowing flower in a rainy cyberpunk alley.", height=120)

if st.button("🚀 Produce My Comic", use_container_width=True, type="primary"):
    try:
        shared_seed = int(time.time()) % 1000000
        style_tags = style_map[art_choice]
        
        with st.status("🎬 Syncing Story & Art...", expanded=True) as status:
            script = generate_comic_script(user_idea, art_choice, num_panels)
            
            panels_out = []
            for i, scene in enumerate(script):
                status.update(label=f"🖌️ Drawing Panel {i+1}: {scene.get('caption')[:30]}...")
                
                # Dynamic mapping
                p_text = scene.get("image_prompt") or scene.get("prompt") or "Comic scene"
                c_text = scene.get("caption") or ""
                
                # Combine style, user seed, and visual prompt
                full_prompt = f"{style_tags}, {p_text}"
                img = generate_image(full_prompt, shared_seed)
                panels_out.append(add_comic_caption(img, c_text))
            
            st.session_state.final_images = panels_out
            
            # PDF Creation
            pdf = FPDF()
            for p in panels_out:
                pdf.add_page(); buf = BytesIO(); p.save(buf, format="PNG")
                pdf.image(buf, x=10, y=10, w=190)
            st.session_state.pdf_bytes = bytes(pdf.output())

            # GIF Creation
            gif_buf = BytesIO()
            st.session_state.final_images[0].save(gif_buf, format="GIF", save_all=True, append_images=st.session_state.final_images[1:], duration=2500, loop=0)
            st.session_state.gif_bytes = gif_buf.getvalue()

            st.session_state.comic_ready = True
            status.update(label="🎉 Production Complete!", state="complete")

    except Exception as e:
        st.error(f"Production Halted: {e}")

if st.session_state.comic_ready:
    col1, col2 = st.columns(2)
    with col1: st.download_button("📄 Download PDF", st.session_state.pdf_bytes, "comic.pdf", "application/pdf", use_container_width=True)
    with col2: st.download_button("🎞️ Download GIF", st.session_state.gif_bytes, "comic.gif", "image/gif", use_container_width=True)

    st.markdown("---")
    cols = st.columns(2)
    for idx, img in enumerate(st.session_state.final_images):
        with cols[idx % 2]:
            st.markdown('<div class="panel-box">', unsafe_allow_html=True)
            st.image(img, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
