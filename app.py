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
st.set_page_config(page_title="Autonomous Pro AI Comic Studio", page_icon="📓", layout="wide")

try:
    # Use st.secrets instead of hardcoded keys
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

# Session State for storing memory and final deliverables
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
    art_choice = st.selectbox("Art Style Preset", ["Modern Superhero (Marvel/DC)", "Studio Ghibli Anime", "3D Disney/Pixar Style", "Dark Noir (B&W)"])
    
    style_map = {
        "Modern Superhero (Marvel/DC)": "highly detailed comic book art, sharp inks, vibrant colors",
        "Studio Ghibli Anime": "hand-drawn anime style, whimsical, soft lighting",
        "3D Disney/Pixar Style": "octane render, cute proportions, soft shadows",
        "Dark Noir (B&W)": "monochrome, heavy shadows, film noir, gritty ink wash"
    }
    
    st.markdown("---")
    st.info("💡 **Autonomous Consistency:** Panel 1 establishes the identities. The studio then locks that DNA for all future panels automatically.")
    
    if st.button("🔄 Clear & Start New Story"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# ==========================================
# 3. CORE AI FUNCTIONS (UPGRADED)
# ==========================================
def fetch_from_api_with_retry(url, headers, payload, max_retries=3):
    """Robust API caller that handles intermittent timeouts."""
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if attempt < max_retries - 1 and e.response.status_code in [504]:
                time.sleep(3)
                continue
            raise Exception(f"API Error: {e} | Response: {e.response.text}")

def add_comic_caption(img, text):
    """Pro lettering: Dynamic height calculation for the text box."""
    width, height = img.size
    
    # Load Font (Ensures Bangers font is used for stylized look)
    try:
        font = ImageFont.truetype("Bangers-Regular.ttf", 46)
    except IOError:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
        except IOError:
            font = ImageFont.load_default()

    wrapped_text = textwrap.fill(text, width=45)
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), wrapped_text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    
    # Dynamically scale the caption height
    cap_h = th + 80
    new_img = Image.new('RGB', (width, height + cap_h), '#FFFBEB') # Subtle paper tint
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    draw.line([(0, height), (width, height)], fill="black", width=6)
    
    # Perfectly center text in the new space
    tx, ty = (width - tw) / 2, height + (cap_h - th) / 2 - 10
    draw.multiline_text((tx, ty), wrapped_text, fill="black", font=font, align="center")
    
    return new_img

def generate_comic_script(idea, style, panels):
    """UPGRADED: Narrative writer that establishes shared visual anchors."""
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = f"""
    You are an Eisner-Award winning writer. Convert this idea into {panels} storyboard panels.
    STRICT RULES:
    1. Gritty, punchy captions (max 15 words). Narration Box.
    2. Character Identity (CRITICAL): Define strict, shared visual tags for 'Character 1' and 'Character 2'. Repeat these exact tags in EVERY single image_prompt. (e.g. 'Character 1: Aadill, 24yo, dark beard, tan shirt').
    3. Output ONLY a raw JSON list. No chat.
    Format: [ {{"caption": "Narration", "image_prompt": "Stylized scene with visual tags"}} ]
    """
    
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": idea}],
        "temperature": 0.3
    }
    
    res = fetch_from_api_with_retry(url, headers, payload)
    raw_text = res.json()["choices"][0]["message"]["content"]
    
    # Regex to extract JSON from AI's conversational response
    json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))
    else:
        raise Exception("The AI writer made a formatting mistake. Please click 'Produce My Comic' again.")

# Unified generation function for iterative loops
def generate_iterative_panel(prompt, seed, anchor_b64=None):
    """
    UPGRADED: SDXL Generation. Dynamically uses Panel 1 base64 
    as identity guide for future panels.
    """
    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 8, "seed": seed, "steps": 30
    }
    
    # Guidance logic: If anchor_b64 exists, activate guidance
    if anchor_b64:
        payload["init_image"] = anchor_b64
        # Increased strength for stronger facial lock
        payload["image_strength"] = 0.65 
    
    res = fetch_from_api_with_retry(url, headers, payload)
    b64_output_data = res.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64_output_data))), b64_output_data

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
st.title("📓 Autonomous AI Comic Studio")
st.markdown("Write a prompt. Our AI directs the story, establishes the characters, and letters the pages.")

user_idea = st.text_area("📖 What is the story about?", "A rogue AI decides it wants to become a chef in a cyberpunk city, but the local mafia steals its recipes.", height=120)

# Main Generation Button
if st.button("🚀 Produce My Comic", use_container_width=True, type="primary"):
    if not API_KEY:
        st.error("Missing NVIDIA_API_KEY! Please check your secrets.")
    else:
        # Secure memory for this session
        st.session_state.current_identity_anchor = None
        temp_images = []
        
        try:
            with st.status("🎬 Pre-Production: Designing character identities...", expanded=True) as status:
                st.session_state.script_data = generate_comic_script(user_idea, art_choice, num_panels)
                st.write("✅ Script locked! Established characters. SENDING TO ILLUSTRATION TEAM...")
                
                # Setup base64 holder for iterative guidance
                b64_guidance = None
                shared_seed = int(time.time() * 1000) % 1000000
                style_tags = style_map[art_choice]
                
                # -------------------------------------------------------------
                # Panel 1: Establish the 'Neutral Shot' / the identity
                # -------------------------------------------------------------
                first_scene = st.session_state.script_data[0]
                status.update(label="🖌️ Establishing Identity in Panel 1 (Neutral Shot)...", state="running")
                
                panel_1_img, panel_1_b64 = generate_iterative_panel(f"{style_tags}, {first_scene['image_prompt']}", shared_seed, None)
                
                # Secure memory of Panel 1 for future guidance
                status.update(label="✅ Panel 1 locked! Capturing Identity DNA...", state="running")
                b64_guidance = panel_1_b64
                # Lettering Panel 1
                temp_images.append(add_comic_caption(panel_1_img, first_scene['caption']))
                
                # -------------------------------------------------------------
                # Panels 2+: Process with strict guidance from Panel 1
                # -------------------------------------------------------------
                remaining_panels = st.session_state.script_data[1:]
                for i, scene in enumerate(remaining_panels):
                    status.update(label=f"🖌️ Drawing Panel {i+2} of {len(st.session_state.script_data)} (Guidance Locked)...", state="running")
                    
                    # Generate using the guidance b64 from Panel 1
                    img, curr_b64 = generate_iterative_panel(f"{style_tags}, {scene['image_prompt']}", shared_seed, b64_guidance)
                    
                    # Lettering
                    labeled_img = add_comic_caption(img, scene['caption'])
                    temp_images.append(labeled_img)
                
                st.session_state.final_images = temp_images
                status.update(label="🎉 Comic Production Complete!", state="complete")

            # --- Restored PDF Deliverable (Fixes byte error) ---
            pdf = FPDF()
            for p in st.session_state.final_images:
                pdf.add_page()
                buffered = BytesIO()
                p.save(buffered, format="PNG")
                pdf.image(buffered, x=10, y=10, w=190)
            st.session_state.pdf_bytes = bytes(pdf.output())

            # --- Restored GIF Deliverable ---
            gif_buf = BytesIO()
            st.session_state.final_images[0].save(
                gif_buf, format="GIF", save_all=True, append_images=st.session_state.final_images[1:], duration=2500, loop=0
            )
            st.session_state.gif_bytes = gif_buf.getvalue()

            st.session_state.comic_ready = True

        except Exception as e:
            st.error(f"Production Halted: {e}")
            st.session_state.comic_ready = False

# ==========================================
# 5. DISPLAY RESULTS & DOWNLOADS
# ==========================================
if st.session_state.comic_ready:
    st.markdown("### 📥 Download Deliverables")
    export_col1, export_col2 = st.columns(2)
    
    with export_col1:
        st.download_button(
            label="📄 Download PDF Book",
            data=st.session_state.pdf_bytes,
            file_name="autonomous_comic_book.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with export_col2:
        st.download_button(
            label="🎞️ Download Animated GIF Preview",
            data=st.session_state.gif_bytes,
            file_name="comic_motion.gif",
            mime="image/gif",
            use_container_width=True
        )
        
    st.markdown("---")
    # Display panels iteratively in a nice grid
    cols = st.columns(2)
    for idx, img in enumerate(st.session_state.final_images):
        with cols[idx % 2]:
            st.image(img, use_container_width=True)
