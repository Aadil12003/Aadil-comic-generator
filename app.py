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
    .panel-box { border: 2px solid #374151; padding: 10px; border-radius: 8px; background-color: #1f2937; margin-bottom: 20px; }
    h1, h2, h3 { color: #f87171; font-family: 'Arial Black', sans-serif; }
    </style>
""", unsafe_allow_html=True)

if 'comic_ready' not in st.session_state: st.session_state.comic_ready = False
if 'final_images' not in st.session_state: st.session_state.final_images = []
if 'pdf_bytes' not in st.session_state: st.session_state.pdf_bytes = None

# ==========================================
# 2. SIDEBAR TOOLS
# ==========================================
with st.sidebar:
    st.header("🛠️ Director's Tools")
    num_panels = st.number_input("Number of Panels", min_value=1, value=4, step=1)
    
    art_choice = st.selectbox("Art Style Preset", [
        "Modern Superhero (Marvel/DC)", 
        "Studio Ghibli Anime", 
        "3D Disney/Pixar Style",
        "Cyberpunk Neon", 
        "Dark Noir (B&W)"
    ])
    
    style_map = {
        "Modern Superhero (Marvel/DC)": "detailed comic art, dynamic inks, superhero aesthetic",
        "Studio Ghibli Anime": "Studio Ghibli style, hand-painted background, anime character, soft lighting",
        "3D Disney/Pixar Style": "Pixar 3D animation style, big expressive eyes, octane render, soft clay look",
        "Cyberpunk Neon": "futuristic neon digital art, cyberpunk aesthetic, glowing colors",
        "Dark Noir (B&W)": "high contrast monochrome, heavy ink shadows, noir style"
    }
    
    if st.button("🔄 Clear & Start New"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# ==========================================
# 3. CORE AI FUNCTIONS
# ==========================================
def fetch_from_api_with_retry(url, headers, payload):
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response

def add_comic_caption(img, text):
    width, height = img.size
    try:
        font = ImageFont.truetype("Bangers-Regular.ttf", 44)
    except:
        font = ImageFont.load_default()

    wrapped_text = textwrap.fill(text, width=38)
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), wrapped_text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    
    cap_h = th + 100
    new_img = Image.new('RGB', (width, height + cap_h), '#FFFBEB')
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    draw.line([(0, height), (width, height)], fill="black", width=10)
    draw.multiline_text(((width-tw)/2, height + (cap_h-th)/2 - 10), wrapped_text, fill="black", font=font, align="center")
    return new_img

def generate_comic_script(idea, style, panels):
    """UPGRADED: Narrative-Image Synchronization Engine."""
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = f"""
    You are a Master Comic Director. Convert the user's idea into {panels} specific storyboard panels.
    
    STORY-ART SYNC RULES:
    1. Visual Identity: Describe the character's clothing and appearance exactly the same in every panel.
    2. Camera Angles: You MUST assign a camera angle to each panel (e.g. 'Close-up on face', 'Extreme wide shot of landscape', 'Over-the-shoulder shot').
    3. Direct Action: If the caption says the character is smiling, the image_prompt MUST say 'character is smiling broadly'. If they are leaning, the prompt MUST say 'character is leaning forward'.
    4. Progression: Each panel must show a DIFFERENT action than the one before it. 
    5. JSON: [ {{"caption": "...", "image_prompt": "..."}} ]
    """
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": idea}],
        "temperature": 0.1 # Keep it strictly focused on instructions
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
        "cfg_scale": 10, # Higher scale makes AI follow the prompt instructions more strictly
        "seed": seed, 
        "steps": 35
    }
    res = fetch_from_api_with_retry(url, headers, payload)
    b64 = res.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64)))

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
st.title("📓 Professional AI Comic Studio")
user_idea = st.text_area("📖 What is the story about?", "A young girl riding a giant cat discovers a cloud castle.", height=100)

if st.button("🚀 Produce My Comic", use_container_width=True, type="primary"):
    try:
        shared_seed = int(time.time()) % 1000000
        style_tags = style_map[art_choice]
        
        with st.status(f"🎬 Synching Story & Art...", expanded=True) as status:
            script = generate_comic_script(user_idea, art_choice, num_panels)
            
            panels_out = []
            for i, scene in enumerate(script):
                # We blend the style tags with the specific action prompt from the script
                full_prompt = f"{style_tags}, {scene.get('image_prompt', 'Comic scene')}"
                c_text = scene.get("caption", "")
                
                status.update(label=f"🖌️ Illustrating Panel {i+1}: {c_text[:40]}...")
                img = generate_image(full_prompt, shared_seed)
                panels_out.append(add_comic_caption(img, c_text))
            
            st.session_state.final_images = panels_out
            
            # PDF Creation
            pdf = FPDF()
            for p in panels_out:
                pdf.add_page(); buf = BytesIO(); p.save(buf, format="PNG")
                pdf.image(buf, x=10, y=10, w=190)
            st.session_state.pdf_bytes = bytes(pdf.output())
            
            st.session_state.comic_ready = True
            status.update(label="🎉 Story Synced Successfully!", state="complete")

    except Exception as e:
        st.error(f"Error: {e}")

if st.session_state.comic_ready:
    col1, col2 = st.columns(2)
    with col1: st.download_button("📄 Download PDF", st.session_state.pdf_bytes, "comic.pdf", "application/pdf")
    with col2:
        gif_buf = BytesIO(); st.session_state.final_images[0].save(gif_buf, format="GIF", save_all=True, append_images=st.session_state.final_images[1:], duration=2500, loop=0)
        st.download_button("🎞️ Download GIF Preview", gif_buf.getvalue(), "comic.gif", "image/gif")

    st.markdown("---")
    cols = st.columns(2)
    for idx, img in enumerate(st.session_state.final_images):
        with cols[idx % 2]: st.image(img, use_container_width=True)
