import streamlit as st
import requests
import base64
from fpdf import FPDF
from io import BytesIO
from PIL import Image

# 1. Setup Page
st.set_page_config(page_title="NVIDIA AI Comic Generator", page_icon="🎨")
st.title("🎨 NVIDIA AI Comic Generator")

# 2. Sidebar for API Key
with st.sidebar:
    st.markdown("### API Settings")
    # Using NVIDIA API key
    api_key = st.text_input("NVIDIA API Key", type="password", help="Get this from build.nvidia.com")
    if not api_key:
        st.warning("Please enter your NVIDIA API key to continue.")

# 3. App Logic
if api_key:
    prompt = st.text_area("Describe your comic scene:", "A brave knight fighting a digital dragon in a neon forest.")
    
    if st.button("Generate Comic Page"):
        with st.spinner("Generating image via NVIDIA Stable Diffusion XL..."):
            try:
                # ---------------------------------------------------------
                # NVIDIA API Integration
                # ---------------------------------------------------------
                invoke_url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                }
                
                payload = {
                    "text_prompts": [
                        {
                            "text": f"Comic book style, high quality, vibrant colors: {prompt}",
                            "weight": 1
                        }
                    ],
                    "cfg_scale": 5,
                    "sampler": "K_DPM_2_ANCESTRAL",
                    "seed": 0,
                    "steps": 25
                }

                # Make the request to NVIDIA
                response = requests.post(invoke_url, headers=headers, json=payload)
                response.raise_for_status() # Check for errors (like an invalid key)
                
                # NVIDIA returns images as base64 encoded strings
                response_json = response.json()
                base64_image_data = response_json["artifacts"][0]["base64"]
                img_data = base64.b64decode(base64_image_data)
                
                # Show image in Streamlit
                st.image(img_data, caption="Your Generated Comic Panel")
                
                # ---------------------------------------------------------
                # 4. Generate PDF
                # ---------------------------------------------------------
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(0, 10, "Your AI Comic", ln=True, align='C')
                
                # Save temp image so FPDF can read it
                img = Image.open(BytesIO(img_data))
                img_path = "temp_comic.png"
                img.save(img_path)
                
                # Add image to PDF
                pdf.image(img_path, x=10, y=30, w=190)
                pdf_output = pdf.output()
                
                st.download_button(
                    label="Download as PDF",
                    data=bytes(pdf_output),
                    file_name="comic_page.pdf",
                    mime="application/pdf"
                )
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 401:
                    st.error("Error 401: Unauthorized. Please check if your NVIDIA API key is correct and active.")
                else:
                    st.error(f"NVIDIA API Error: {response.text}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

else:
    st.info("Waiting for NVIDIA API key...")
