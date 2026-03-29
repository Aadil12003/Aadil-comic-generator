import streamlit as st
import requests
import base64
import json
import re
from fpdf import FPDF
from io import BytesIO
from PIL import Image

# ==========================================
# 1. UI SETUP & STYLING
# ==========================================
st.set_page_config(page_title="AI Comic Studio", page_icon="📓", layout="wide")

# Custom CSS for a better UI
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .panel-box { border: 2px solid #333; padding: 10px; border-radius: 10px; background-color: #1E1E1E; }
    h1, h2, h3 { color: #FF4B4B; }
    </style>
""", unsafe_allow_html=True)

st.title("📓 Professional AI Comic Studio")
st.markdown("Write the idea. The AI directs the scenes, keeps characters consistent, and draws the panels.")

# ==========================================
# 2. SIDEBAR (API & SETTINGS)
# ==========================================
with st.sidebar:
    st.header("⚙️ Studio Settings")
    api_key = st.text_input("NVIDIA API Key", type="password")
    
    st.markdown("---")
    num_panels = st.slider("Number of Panels", min_value=1, max_value=4, value=2, 
                          help="More panels take longer to generate.")
    
    if not api_key:
        st.warning("⚠️ Enter your NVIDIA API key to unlock the studio.")

# ==========================================
# 3. CORE FUNCTIONS
# ==========================================
def generate_comic_script(idea, key, panels):
    """Calls NVIDIA LLaMA 3 to act as the Comic Director and write the JSON script."""
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = f"""
    You are a professional comic book writer and visual director.
    Convert the user's idea into a strictly formatted JSON array containing exactly {panels} scenes.
    
    RULES:
    - Character consistency is top priority. Never change appearance across scenes.
    - Output ONLY valid JSON. No markdown formatting, no explanations.
    
    JSON STRUCTURE EXPECTED:
    [
      {{
        "scene_number": 1,
        "story_context": "Brief what is happening",
        "dialogue": "Character: Hello!",
        "image_prompt": "Comic book style, high quality. [Character exact appearance]. [Action]. [Background]. [Lighting]."
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
        "max_tokens": 1024
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    # Clean the output just in case the AI adds markdown ticks
    raw_text = response.json()["choices"][0]["message"]["content"]
    clean_text = re.sub(r'```json|```', '', raw_text).strip()
    return json.loads(clean_text)

def generate_image(prompt, key):
    """Calls NVIDIA SDXL to generate the panel image."""
    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 5,
        "sampler": "K_DPM_2_ANCESTRAL",
        "seed": 0,
        "steps": 25
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    b64_data = response.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64_data)))

# ==========================================
# 4. MAIN APP LOGIC
# ==========================================
if api_key:
    user_idea = st.text_area("📖 Story Idea", "A cyberpunk detective finds a glowing neon flower in a digital alleyway.", height=100)
    
    if st.button("🎬 Produce Comic", use_container_width=True, type="primary"):
        
        # Initialize storage for exports
        generated_images = []
        script_data = []
        
        try:
            # STEP 1: Director writes the script
            with st.status("📝 Director is writing the script and designing characters...", expanded=True) as status:
                script_data = generate_comic_script(user_idea, api_key, num_panels)
                st.write("Script finalized! Moving to illustration...")
                
                # STEP 2: Illustrator draws the panels
                cols = st.columns(num_panels)
                
                for i, scene in enumerate(script_data):
                    status.update(label=f"🎨 Illustrating Panel {i+1} of {num_panels}...", state="running")
                    
                    # Generate the image
                    img = generate_image(scene["image_prompt"], api_key)
                    generated_images.append(img)
                    
                    # Display in UI visually
                    with cols[i]:
                        st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
                        st.image(img, use_container_width=True)
                        st.caption(f"**Scene {scene['scene_number']}**")
                        st.write(f"*{scene['dialogue']}*")
                        with st.expander("View Director's Prompt"):
                            st.write(scene["image_prompt"])
                        st.markdown("</div>", unsafe_allow_html=True)
                
                status.update(label="✅ Comic Production Complete!", state="complete")

            # ==========================================
            # 5. EXPORT OPTIONS (PDF & GIF)
            # ==========================================
            st.markdown("### 📥 Download Your Comic")
            export_col1, export_col2 = st.columns(2)
            
            # Export 1: Build PDF
            pdf = FPDF()
            for i, img in enumerate(generated_images):
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 10, f"Panel {i+1}: {script_data[i]['dialogue']}", ln=True, align='C')
                
                # Save temp image for PDF
                temp_path = f"temp_{i}.png"
                img.save(temp_path)
                pdf.image(temp_path, x=10, y=30, w=190)
                
            pdf_bytes = bytes(pdf.output())
            
            with export_col1:
                st.download_button(
                    label="📄 Download Comic as PDF",
                    data=pdf_bytes,
                    file_name="my_ai_comic.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            # Export 2: Build Animated GIF (Video Alternative)
            gif_buffer = BytesIO()
            generated_images[0].save(
                gif_buffer, format="GIF",
                save_all=True,
                append_images=generated_images[1:],
                duration=2000, # 2 seconds per panel
                loop=0
            )
            gif_bytes = gif_buffer.getvalue()
            
            with export_col2:
                st.download_button(
                    label="🎞️ Download Animated Comic (GIF)",
                    data=gif_bytes,
                    file_name="animated_comic.gif",
                    mime="image/gif",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"Production Halted! Error: {e}")
