import streamlit as st
import requests
import base64
import json
import re
import textwrap
from fpdf import FPDF
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. STUDIO CONFIGURATION & SECRETS
# ==========================================
st.set_page_config(page_title="Pro AI Comic Studio", page_icon="📓", layout="wide")

# PUT YOUR NVIDIA API KEY HERE (Since you pasted it in the background)
# Alternatively, use st.secrets["NVIDIA_API_KEY"] if using Streamlit Secrets
API_KEY = "YOUR_NVIDIA_API_KEY_HERE" 

# Custom CSS for a premium dark mode UI
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #ffffff; }
    .stSidebar { background-color: #111827; }
    .panel-box { border: 1px solid #374151; padding: 15px; border-radius: 12px; background-color: #1f2937; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); }
    h1, h2, h3 { color: #f87171; font-family: 'Arial Black', sans-serif; }
    .comic-text { font-style: italic; color: #9ca3af; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SIDEBAR (TOOLS & SETTINGS)
# ==========================================
with st.sidebar:
    st.header("🛠️ Director's Tools")
    
    # Unlimited panels
    num_panels = st.number_input("Number of Panels", min_value=1, value=4, step=1, help="Choose how long your comic will be.")
    
    # Comic Styles
    st.markdown("### 🎨 Art Direction")
    art_style = st.selectbox(
        "Comic Style", 
        ["Modern American Comic (Marvel/DC)", "Classic Vintage Comic", "Japanese Manga (Black & White)", "Dark Noir Graphic Novel", "Vibrant Cyberpunk", "Watercolor Storybook"]
    )
    
    # Reference Image Upload
    st.markdown("### 🖼️ Character Reference (Optional)")
    reference_image = st.file_uploader("Upload a face/character reference", type=['png', 'jpg', 'jpeg'])
    if reference_image:
        st.success("Reference image loaded! It will guide the character design.")

# ==========================================
# 3. CORE AI FUNCTIONS
# ==========================================
def add_comic_caption(img, text):
    """Adds a white caption box with text at the bottom of the image."""
    width, height = img.size
    caption_height = 180 # Height of the text box
    
    # Create a new image with space for the text
    new_img = Image.new('RGB', (width, height + caption_height), '#ffffff')
    new_img.paste(img, (0, 0))
    
    draw = ImageDraw.Draw(new_img)
    
    # Wrap text so it fits inside the image width
    # (Adjust width=60 depending on the font size and image width)
    wrapped_text = textwrap.fill(text, width=70)
    
    # Load default font (For better results, you can upload a .ttf file to your repo and use ImageFont.truetype("font.ttf", 30))
    # Using default here to ensure it works immediately without external files
    try:
        font = ImageFont.truetype("arial.ttf", 24) # Tries to use Arial if available on system
    except IOError:
        font = ImageFont.load_default()
        
    # Draw text in black
    draw.text((20, height + 20), wrapped_text, fill="black", font=font)
    return new_img

def generate_comic_script(idea, style, panels):
    """Calls NVIDIA LLaMA 3 to act as the Comic Director."""
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = f"""
    You are a master comic book writer. Convert the user's idea into a {panels}-panel story.
    Make the storytelling captivating, dramatic, and emotional.
    
    RULES:
    - Character consistency is CRITICAL. Define exact appearance (clothes, hair, face) and repeat it exactly in every image prompt.
    - Output strictly valid JSON.
    
    JSON STRUCTURE:
    [
      {{
        "scene_number": 1,
        "caption": "A dramatic narration or dialogue box to put on the image.",
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
        "temperature": 0.4,
        "max_tokens": 1500
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    clean_text = re.sub(r'```json|```', '', response.json()["choices"][0]["message"]["content"]).strip()
    return json.loads(clean_text)

def generate_image(prompt, ref_image=None):
    """Calls NVIDIA SDXL to generate the panel, using a reference image if provided."""
    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 6,
        "sampler": "K_DPM_2_ANCESTRAL",
        "seed": 0,
        "steps": 30
    }
    
    # If user uploaded a reference image, encode it and add to payload (Image-to-Image)
    if ref_image:
        ref_bytes = ref_image.getvalue()
        base64_ref = base64.b64encode(ref_bytes).decode('utf-8')
        payload["init_image"] = base64_ref
        payload["image_strength"] = 0.35 # How much the reference controls the output
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    b64_data = response.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64_data)))

# ==========================================
# 4. MAIN DASHBOARD
# ==========================================
st.title("📓 Professional AI Comic Studio")
st.markdown("Write a prompt. Our AI directs the scenes, illustrates the art, and letters the pages.")

user_idea = st.text_area("📖 What is the story about?", "A rogue AI decides it wants to become a chef in a cyberpunk city, but the local mafia steals its recipes.", height=120)

if st.button("🚀 Produce My Comic", use_container_width=True, type="primary"):
    
    generated_images = []
    script_data = []
    
    try:
        with st.status("🎬 Pre-Production: Writing script & designing characters...", expanded=True) as status:
            script_data = generate_comic_script(user_idea, art_style, num_panels)
            st.write("✅ Script locked in! Sending to illustration team...")
            
            # Create a nice visual grid based on panel count
            cols = st.columns(2) # 2 panels per row
            
            for i, scene in enumerate(script_data):
                status.update(label=f"🖌️ Illustrating & Lettering Panel {i+1} of {num_panels}...", state="running")
                
                # 1. Generate Base Image
                base_img = generate_image(scene["image_prompt"], reference_image)
                
                # 2. Add Story/Caption directly onto the image
                final_img = add_comic_caption(base_img, scene["caption"])
                generated_images.append(final_img)
                
                # 3. Display in UI
                col_index = i % 2
                with cols[col_index]:
                    st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
                    st.image(final_img, use_container_width=True)
                    st.markdown(f"**Scene {scene['scene_number']}**")
                    with st.expander("Technical Prompt"):
                        st.caption(scene["image_prompt"])
                    st.markdown("</div><br>", unsafe_allow_html=True)
            
            status.update(label="🎉 Comic Production Complete!", state="complete")

        # ==========================================
        # 5. EXPORT OPTIONS
        # ==========================================
        st.markdown("---")
        st.markdown("### 📥 Download Deliverables")
        export_col1, export_col2 = st.columns(2)
        
        # PDF Export
        pdf = FPDF()
        for i, img in enumerate(generated_images):
            pdf.add_page()
            temp_path = f"temp_final_{i}.png"
            img.save(temp_path)
            # Center the image on the PDF page
            pdf.image(temp_path, x=20, y=20, w=170)
            
        pdf_bytes = bytes(pdf.output())
        with export_col1:
            st.download_button("📄 Download PDF Book", data=pdf_bytes, file_name="ai_comic_book.pdf", mime="application/pdf", use_container_width=True)

        # Video/GIF Export
        gif_buffer = BytesIO()
        generated_images[0].save(
            gif_buffer, format="GIF", save_all=True, append_images=generated_images[1:], duration=2500, loop=0
        )
        with export_col2:
            st.download_button("🎞️ Download Animated Video (GIF)", data=gif_buffer.getvalue(), file_name="comic_motion.gif", mime="image/gif", use_container_width=True)

    except Exception as e:
        st.error(f"Production Halted! Error details: {e}")
