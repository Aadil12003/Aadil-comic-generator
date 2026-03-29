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

# Securely grab the API key from Streamlit Cloud Secrets
try:
    API_KEY = st.secrets["NVIDIA_API_KEY"]
except Exception:
    API_KEY = None

# Custom CSS for a premium dark mode UI
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
        st.error("⚠️ NVIDIA_API_KEY is missing from Streamlit Secrets!")
    
    num_panels = st.number_input("Number of Panels", min_value=1, value=4, step=1, help="Choose how long your comic will be.")
    
    st.markdown("### 🎨 Art Direction")
    art_style = st.selectbox(
        "Comic Style", 
        ["Modern American Comic (Marvel/DC)", "Classic Vintage Comic", "Japanese Manga (Black & White)", "Dark Noir Graphic Novel", "Vibrant Cyberpunk", "Watercolor Storybook"]
    )
    
    st.markdown("### 🖼️ Character Reference (Optional)")
    reference_image = st.file_uploader("Upload a face/character reference", type=['png', 'jpg', 'jpeg'])
    if reference_image:
        st.success("Reference image loaded! It will guide the character design.")

# ==========================================
# 4. CORE AI FUNCTIONS WITH RETRY LOGIC
# ==========================================
def fetch_from_api_with_retry(url, headers, payload, max_retries=3):
    """Robust API caller that handles 504 timeouts and retries automatically."""
    for attempt in range(max_retries):
        try:
            # Added a 60-second timeout to wait for NVIDIA
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1)) # Wait longer before each retry
                continue
            else:
                raise Exception(f"API Failed after {max_retries} attempts. Error: {e}")

def add_comic_caption(img, text):
    """Adds a white caption box with text at the bottom of the image."""
    width, height = img.size
    caption_height = 180 
    
    new_img = Image.new('RGB', (width, height + caption_height), '#ffffff')
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    wrapped_text = textwrap.fill(text, width=60)
    
    try:
        font = ImageFont.truetype("Bangers-Regular.ttf", 32) 
    except IOError:
        font = ImageFont.load_default()
        
    draw.text((20, height + 20), wrapped_text, fill="black", font=font)
    return new_img

def generate_comic_script(idea, style, panels):
    """Calls NVIDIA LLaMA 3 to act as the Comic Director."""
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = f"""
    You are a master comic book writer. Convert the user's idea into a {panels}-panel story.
    
    CRITICAL JSON RULES:
    1. Output ONLY a valid JSON array. NO conversational text before or after the JSON.
    2. Start your response with [ and end with ].
    3. DO NOT use double quotes (") inside your string values. Use single quotes (') instead.
    4. Character consistency is CRITICAL. Define exact appearance (clothes, hair, face) and repeat it exactly in every prompt.
    
    JSON STRUCTURE:
    [
      {{
        "scene_number": 1,
        "caption": "A dramatic narration or dialogue box.",
        "image_prompt": "{style} style, high quality. [Exact Character Description]. [Action]. [Environment]."
      }}
    ]
    """
    
    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"My comic idea: {idea}"}
        ],
        "temperature": 0.3,
        "max_tokens": 2000 
    }
    
    response = fetch_from_api_with_retry(url, headers, payload)
    raw_text = response.json()["choices"][0]["message"]["content"]
    
    # Bulletproof extraction
    match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    clean_text = match.group(0) if match else raw_text
    
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        print(f"FAILED TO PARSE JSON. RAW AI OUTPUT WAS:\n{raw_text}")
        raise Exception("The AI writer made a formatting error in the script. Please click 'Produce My Comic' again to regenerate!")

def generate_image(prompt, ref_image=None):
    """Calls NVIDIA SDXL to generate the panel."""
    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 6,
        "sampler": "K_DPM_2_ANCESTRAL",
        "seed": 0,
        "steps": 30
    }
    
    if ref_image:
        ref_bytes = ref_image.getvalue()
        base64_ref = base64.b64encode(ref_bytes).decode('utf-8')
        payload["init_image"] = base64_ref
        payload["image_strength"] = 0.35 
    
    response = fetch_from_api_with_retry(url, headers, payload)
    b64_data = response.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64_data)))

# ==========================================
# 5. MAIN DASHBOARD
# ==========================================
st.title("📓 Professional AI Comic Studio")
st.markdown("Write a prompt. Our AI directs the scenes, illustrates the art, and letters the pages.")

user_idea = st.text_area("📖 What is the story about?", "A rogue AI decides it wants to become a chef in a cyberpunk city, but the local mafia steals its recipes.", height=120)

# Generate Button Logic
if st.button("🚀 Produce My Comic", use_container_width=True, type="primary"):
    if not API_KEY:
        st.error("Cannot generate: API Key is missing. Check your Streamlit Secrets.")
    else:
        try:
            with st.status("🎬 Pre-Production: Writing script & designing characters...", expanded=True) as status:
                st.session_state.script_data = generate_comic_script(user_idea, art_style, num_panels)
                st.write("✅ Script locked in! Sending to illustration team...")
                
                temp_images = []
                for i, scene in enumerate(st.session_state.script_data):
                    status.update(label=f"🖌️ Illustrating & Lettering Panel {i+1} of {num_panels}...", state="running")
                    
                    base_img = generate_image(scene["image_prompt"], reference_image)
                    final_img = add_comic_caption(base_img, scene["caption"])
                    temp_images.append(final_img)
                
                st.session_state.final_images = temp_images
                status.update(label="🎉 Comic Production Complete!", state="complete")

            # Prepare Downloads
            pdf = FPDF()
            for i, img in enumerate(st.session_state.final_images):
                pdf.add_page()
                temp_path = f"temp_final_{i}.png"
                img.save(temp_path)
                pdf.image(temp_path, x=20, y=20, w=170)
            st.session_state.pdf_bytes = bytes(pdf.output())

            gif_buffer = BytesIO()
            st.session_state.final_images[0].save(
                gif_buffer, format="GIF", save_all=True, append_images=st.session_state.final_images[1:], duration=2500, loop=0
            )
            st.session_state.gif_bytes = gif_buffer.getvalue()

            st.session_state.comic_ready = True

        except Exception as e:
            st.error(f"Production Halted! Error details: {e}")
            st.session_state.comic_ready = False

# ==========================================
# 6. DISPLAY RESULTS & DOWNLOADS
# ==========================================
if st.session_state.comic_ready:
    st.markdown("---")
    cols = st.columns(2) 
    
    for i, (scene, img) in enumerate(zip(st.session_state.script_data, st.session_state.final_images)):
        col_index = i % 2
        with cols[col_index]:
            st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
            st.image(img, use_container_width=True)
            st.markdown(f"**Scene {scene['scene_number']}**")
            with st.expander("Technical Prompt"):
                st.caption(scene["image_prompt"])
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### 📥 Download Deliverables")
    export_col1, export_col2 = st.columns(2)
    
    with export_col1:
        st.download_button("📄 Download PDF Book", data=st.session_state.pdf_bytes, file_name="ai_comic_book.pdf", mime="application/pdf", use_container_width=True)

    with export_col2:
        st.download_button("🎞️ Download Animated Video (GIF)", data=st.session_state.gif_bytes, file_name="comic_motion.gif", mime="image/gif", use_container_width=True)
        
    st.markdown("---")
    # New Reset Button
    if st.button("🔄 Start New Comic", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
