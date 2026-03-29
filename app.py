import streamlit as st
from openai import OpenAI
from fpdf import FPDF
import requests
from io import BytesIO
from PIL import Image

# 1. Setup Page
st.set_page_config(page_title="AI Comic Generator", page_icon="🎨")
st.title("🎨 AI Comic Generator")

# 2. Sidebar for API Key
with st.sidebar:
    api_key = st.text_input("OpenAI API Key", type="password")
    if not api_key:
        st.warning("Please enter your OpenAI API key to continue.")

# 3. App Logic
if api_key:
    client = OpenAI(api_key=api_key)
    
    prompt = st.text_area("Describe your comic scene:", "A brave knight fighting a digital dragon in a neon forest.")
    
    if st.button("Generate Comic Page"):
        with st.spinner("Generating image..."):
            try:
                # Generate Image using DALL-E 3
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=f"Comic book style, high quality, vibrant colors: {prompt}",
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                
                image_url = response.data[0].url
                img_data = requests.get(image_url).content
                st.image(img_data, caption="Your Generated Comic Panel")
                
                # 4. Generate PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(0, 10, "Your AI Comic", ln=True, align='C')
                
                # Save temp image for PDF
                img = Image.open(BytesIO(img_data))
                img_path = "temp_comic.png"
                img.save(img_path)
                
                pdf.image(img_path, x=10, y=30, w=190)
                pdf_output = pdf.output()
                
                st.download_button(
                    label="Download as PDF",
                    data=bytes(pdf_output),
                    file_name="comic_page.pdf",
                    mime="application/pdf"
                )
                
            except Exception as e:
                st.error(f"An error occurred: {e}")

else:
    st.info("Waiting for API key...")
