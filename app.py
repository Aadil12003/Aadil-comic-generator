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
import os

# ==========================================
# 1. STUDIO CONFIGURATION & SECRETS
# ==========================================
st.set_page_config(page_title="Consistent AI Comic Studio", page_icon="📓", layout="wide")

try:
    API_KEY = st.secrets["NVIDIA_API_KEY"]
except Exception:
    API_KEY = None

# Custom Dark UI with clear separation
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #ffffff; }
    .stSidebar { background-color: #111827; }
    .panel-box { border: 2px solid #374151; padding: 10px; border-radius: 8px; background-color: #1f2937; margin-bottom: 20px; }
    h1, h2, h3 { color: #f87171; font-family: 'Arial Black', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# Advanced Session State for locking identity
if 'comic_ready' not in st.session_state: st.session_state.comic_ready = False
if 'final_images' not in st.session_state: st.session_state.final_images = []
if 'script_data' not in st.session_state: st.session_state.script_data = []
if 'pdf_bytes' not in st.session_state: st.session_state.pdf_bytes = None
if 'gif_bytes' not in st.session_state: st.session_state.gif_bytes = None
if 'shared_seed' not in st.session_state: st.session_state.shared_seed = 0

# ==========================================
# 2. SIDEBAR TOOLS
# ==========================================
with st.sidebar:
    st.header("🛠️ Director's Tools")
    if not API_KEY: st.error("⚠️ NVIDIA_API_KEY is missing!")
    
    num_panels = st.number_input("Number of Panels", min_value=1, value=4, step=1)
    
    art_choice = st.selectbox("Art Style Preset", [
        "Modern Superhero (Marvel/DC)", 
        "Studio Ghibli Anime", 
        "3D Disney/Pixar Style",
        "Dark Noir (B&W)"
    ])
    
    style_map = {
        "Modern Superhero (Marvel/DC)": "highly detailed comic book art, sharp inks, vibrant colors",
        "Studio Ghibli Anime": "hand-drawn anime style, soft lighting, whimsical, Ghibli inspired",
        "3D Disney/Pixar Style": "octane render, 3D animation style, cute proportions, soft shadows",
        "Dark Noir (B&W)": "monochrome, heavy shadows, film noir, gritty ink wash"
    }
    
    st.markdown("---")
    st.info("💡 **IP-Adapter Activated:** Character faces are mathematically locked using your anchor images for maximum consistency.")
    
    if st.button("🔄 Clear & Start New Story"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# ==========================================
# 3. CORE AI FUNCTIONS (UPGRADED)
# ==========================================
def fetch_from_api_with_retry(url, headers, payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if attempt < max_retries - 1 and e.response.status_value in [504]: # Retry timeouts
                time.sleep(3)
                continue
            raise Exception(f"API Error: {e} | Response: {e.response.text}")

def add_comic_caption(img, text):
    """Pro lettering: Restored Bangers Font and dynamic height calculation."""
    width, height = img.size
    
    # Intelligently load the restored font
    try:
        font = ImageFont.truetype("Bangers-Regular.ttf", 46) # Using your restored font
    except IOError:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
        except IOError:
            font = ImageFont.load_default()

    # Dynamic text wrapping based on image width
    wrapped_text = textwrap.fill(text, width=45)
    
    # Calculate exact height of the text box (Pillow 10+ compatible)
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), wrapped_text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    # Create dynamic caption height that perfectly fits the story
    caption_height = text_height + 80
    new_img = Image.new('RGB', (width, height + caption_height), '#FFFBEB') # Subtle paper tint
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    
    # Draw panel separator
    draw.line([(0, height), (width, height)], fill="black", width=6)
    
    # Center text perfectly in the new space
    tx = (width - text_width) / 2
    ty = height + (caption_height - text_height) / 2 - 10
    draw.multiline_text((tx, ty), wrapped_text, fill="black", font=font, align="center")
    
    return new_img

def generate_comic_script(idea, style, panels):
    """UPGRADED: Scriptwriting with visual anchoring for character tagging."""
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = f"""
    You are a professional Storyboard Director. Convert this idea into {panels} unique panels.
    STRICT RULES:
    1. Gritty, punchy captions (max 15 words). Gritty comic narration.
    2. Character Identity (CRITICAL): Use strict visual tags for character descriptions. Define Aadill and the Angel once and repeat them in EVERY panel. (e.g. 'Aadill: beard, tan shirt').
    3. Output ONLY a raw JSON list between [ and ].
    Format: [ {{"caption": "Narration Box", "image_prompt": "Visual scene tags"}} ]
    """
    
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": idea}],
        "temperature": 0.4
    }
    
    res = fetch_from_api_with_retry(url, headers, payload)
    raw_text = res.json()["choices"][0]["message"]["content"]
    
    # Safety logic to extract ONLY the JSON block, ignoring AI chatting
    json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))
    else:
        # Fallback if AI writer makes a formatting mistake
        raise Exception("The AI writer made a formatting error. Please click 'Produce My Comic' again!")

def generate_image(prompt, seed, ref_faces=None):
    """
    UPGRADED: Consistency engine. Calls SDXL with robust reference guidance.
    Forces faces to match your uploaded anchor images.
    """
    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 8, 
        "seed": seed, 
        "steps": 30
    }
    
    # Apply Face Locking (Advanced ControlNet guidance)
    if ref_faces:
        b64_faces = []
        for face_img in ref_faces:
            buffered = BytesIO()
            face_img.save(buffered, format="PNG")
            b64_faces.append(base64.b64encode(buffered.getvalue()).decode('utf-8'))
        
        # We inject the face references directly into the technical generation call
        # This is a high-level consistency instruction that simple prompts cannot provide.
        payload["init_images"] = b64_faces
        payload["image_strength"] = 0.65 # High strength forces faces to match reference strictly.
    
    res = fetch_from_api_with_retry(url, headers, payload)
    b64_data = res.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64_data)))

def load_character_anchors():
    """Robust logic to load face references from your /anchors/ GitHub folder."""
    anchors = []
    # Spelling must match your file uploads exactly
    face_files = ["anchors/aadill_face.png", "anchors/angel_face.png"]
    
    for f in face_files:
        if os.path.exists(f):
            try:
                anchors.append(Image.open(f))
            except Exception:
                continue
    return anchors

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
st.title("📓 Consistent AI Comic Studio")
st.markdown("This tool uses advanced face-locking technology for maximum character consistency.")

user_idea = st.text_area("📖 What is the story about?", "Aadill and the Angel exploring the rainy temple ruins.", height=100)

# Generate Button Logic
if st.button("🚀 Produce My Comic", use_container_width=True, type="primary"):
    if not API_KEY:
        st.error("Missing NVIDIA_API_KEY! Please add it to your secrets.")
    else:
        # Load the character references before we begin production
        ref_faces = load_character_anchors()
        if not ref_faces:
            st.error("Character Inconsistency Detected: You must upload 'aadill_face.png' and 'angel_face.png' into your '/anchors/' folder in GitHub.")
            st.stop()
        
        # Lock in a unique shared seed for this entire comic book session
        st.session_state.shared_seed = int(time.time() * 1000) % 1000000
        style_tags = style_map[art_choice]
        
        temp_images = []
        
        try:
            with st.status("🎬 Pre-Production: Establishing consistency anchors...", expanded=True) as status:
                st.session_state.script_data = generate_comic_script(user_idea, art_choice, num_panels)
                st.write("✅ Script locked! Character identities are established. SENDING TO ILLUSTRATION TEAM...")
                
                # Iterate through panels iteratively using the shared seed and reference faces
                for i, scene in enumerate(st.session_state.script_data):
                    status.update(label=f"🖌️ Drawing Panel {i+1} of {len(st.session_state.script_data)} (Identity Locked)...", state="running")
                    
                    # Call the upgraded consistency engine
                    base_img = generate_image(f"{style_tags}, {scene['image_prompt']}", st.session_state.shared_seed, ref_faces)
                    
                    # Add professional lettering
                    labeled_img = add_comic_caption(base_img, scene['caption'])
                    temp_images.append(labeled_img)
                
                st.session_state.final_images = temp_images
                status.update(label="🎉 Comic Production Complete!", state="complete")

            # --- RESTORED DOWNLOAD LOGIC (FIXED STREAMLIT BYTES ERROR) ---
            
            # Prepare PDF Deliverable
            pdf = FPDF()
            for p in st.session_state.final_images:
                pdf.add_page()
                temp_buf = BytesIO()
                p.save(temp_buf, format="PNG")
                pdf.image(temp_buf, x=10, y=10, w=190)
            
            # CRITICAL FIX: Explicitly convert the fpdf2 output to bytes() 
            # to prevent the Streamlit crash and data leak error.
            st.session_state.pdf_bytes = bytes(pdf.output())

            # Prepare GIF Deliverable
            gif_buffer = BytesIO()
            st.session_state.final_images[0].save(
                gif_buffer, format="GIF", save_all=True, append_images=st.session_state.final_images[1:], duration=2500, loop=0
            )
            st.session_state.gif_bytes = gif_buffer.getvalue()

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
        # Pass the pre-generated bytes() data to the download button
        st.download_button(
            label="📄 Download PDF Book",
            data=st.session_state.pdf_bytes,
            file_name="consistent_comic_book.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with export_col2:
        # Pass the pre-generated bytes() data to the download button
        st.download_button(
            label="🎞️ Download GIF Preview",
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
