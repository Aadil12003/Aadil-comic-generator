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
        "Modern Superhero (Marvel/DC)": "highly detailed comic book art, sharp inks, vibrant colors",
        "Studio Ghibli Anime": "hand-drawn anime style, soft lighting, Ghibli inspired",
        "3D Disney/Pixar Style": "octane render, 3D animation style, soft shadows",
        "Cyberpunk Neon": "futuristic digital art, glowing neon lights, synthwave",
        "Dark Noir (B&W)": "monochrome, heavy shadows, film noir, gritty"
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

def add_overlay_labels(img, labels):
    """
    FIX: Draws text directly on the image (like the sample provided) 
    instead of in a separate box at the bottom.
    """
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("Bangers-Regular.ttf", 40)
    except:
        font = ImageFont.load_default()

    # We position labels at fixed 'hotspots' to mimic the sample
    positions = [(50, 50), (600, 100), (50, 800)]
    
    for i, label_text in enumerate(labels[:3]):
        pos = positions[i]
        # Draw text shadow for readability
        draw.text((pos[0]+2, pos[1]+2), label_text, fill="black", font=font)
        # Draw main white text
        draw.text(pos, label_text, fill="white", font=font)
    
    return img

def generate_comic_script(idea, style, panels):
    """
    UPGRADED: Learns from your sample to include character age/labels.
    """
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = f"""
    You are a professional Storyboard Director.
    TASK: Convert this idea into {panels} panels.
    
    CONSISTENCY RULES:
    1. Define 'Character 1' and 'Character 2' visual tags (e.g. 'Aadill: 24yo, beard, tan shirt').
    2. Repeat these tags in EVERY panel's image_prompt.
    3. Include 2-3 short 'labels' for each panel (e.g. 'Age: 22', 'Aadill: 24').
    
    Output ONLY a JSON list: 
    [ {{"labels": ["Label 1", "Label 2"], "image_prompt": "..."}} ]
    """
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": idea}],
        "temperature": 0.2
    }
    
    res = fetch_from_api_with_retry(url, headers, payload)
    raw_text = res.json()["choices"][0]["message"]["content"]
    json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    return json.loads(json_match.group(0))

def generate_image(prompt, seed):
    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 9, "seed": seed, "steps": 30
    }
    res = fetch_from_api_with_retry(url, headers, payload)
    b64 = res.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64)))

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
st.title("📓 Character-Consistent Comic Studio")
st.markdown("This tool now places labels directly on images to fix character identity.")

user_idea = st.text_area("📖 Story Idea", "Aadill and the Angel walking through a rainy temple.", height=100)

if st.button("🚀 Produce My Comic", use_container_width=True, type="primary"):
    try:
        shared_seed = int(time.time()) % 1000000
        style_tags = style_map[art_choice]
        
        with st.status(f"🎬 Synching Character Identities...", expanded=True) as status:
            script = generate_comic_script(user_idea, art_choice, num_panels)
            
            panels_out = []
            for i, scene in enumerate(script):
                full_prompt = f"{style_tags}, " + scene.get("image_prompt", "Comic scene")
                labels = scene.get("labels", [])
                
                status.update(label=f"🖌️ Drawing Panel {i+1}...")
                img = generate_image(full_prompt, shared_seed)
                
                # Apply labels directly ON the image
                labeled_img = add_overlay_labels(img, labels)
                panels_out.append(labeled_img)
            
            st.session_state.final_images = panels_out
            st.session_state.comic_ready = True
            status.update(label="🎉 Identity Locked and Generated!", state="complete")

    except Exception as e:
        st.error(f"Error: {e}")

if st.session_state.comic_ready:
    cols = st.columns(2)
    for idx, img in enumerate(st.session_state.final_images):
        with cols[idx % 2]:
            st.image(img, use_container_width=True)
