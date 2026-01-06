import streamlit as st
import time
from PIL import Image
import tempfile
import os
from pathlib import Path
import io

# -------------------- Page Config --------------------
st.set_page_config(
    page_title="Image Converter",
    page_icon="🗃️",
    layout="centered"
)

# -------------------- Custom CSS --------------------
st.markdown("""
<style>
.stProgress > div > div > div > div {
    background-color: #ff4b4b;
}
.block-container {
    padding-top: 2rem;
}
div[data-testid="column"] {
    border: 1px solid #2c2c2c;
    padding: 1rem;
    border-radius: 10px;
    background-color: #0e1117;
}
</style>
""", unsafe_allow_html=True)

# -------------------- Initialize Session State --------------------
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'uploaded_file_path' not in st.session_state:
    st.session_state.uploaded_file_path = None
if 'converted_file_path' not in st.session_state:
    st.session_state.converted_file_path = None
if 'temp_files' not in st.session_state:
    st.session_state.temp_files = []
if 'image_bytes' not in st.session_state:
    st.session_state.image_bytes = None

# -------------------- Cleanup Function --------------------
def cleanup_temp_files():
    """Clean up temporary files from previous runs"""
    files_to_remove = st.session_state.temp_files.copy()
    for temp_file in files_to_remove:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                if temp_file in st.session_state.temp_files:
                    st.session_state.temp_files.remove(temp_file)
        except Exception as e:
            st.warning(f"Could not delete temporary file: {e}")

# -------------------- Image Conversion Function (FIXED) --------------------
def convert_image(input_path, target_format):
    """Convert image to target format and return temp file path"""
    try:
        # Open image
        image = Image.open(input_path)
        
        # Log original image info for debugging
        st.sidebar.info(f"Original: Mode={image.mode}, Size={image.size}, Format={image.format}")
        
        # Check if conversion is needed
        input_ext = Path(input_path).suffix.lower().replace('.', '')
        target_lower = target_format.lower()
        
        # Map JPG to JPEG for PIL
        pil_format = "JPEG" if target_format in ["JPG", "JPEG"] else target_format
        
        if input_ext == target_lower:
            # Same format, just copy with optimized settings
            with open(input_path, 'rb') as src:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{target_lower}') as dst:
                    dst.write(src.read())
                    return dst.name
        
        # Handle JPG/JPEG conversion with transparency
        if target_format in ["JPG", "JPEG"]:
            st.sidebar.info("Converting to JPG/JPEG format...")
            
            # Convert image to RGB, handling all transparency cases
            if image.mode in ("RGBA", "LA", "P"):
                # For images with transparency
                if image.mode == "P" and "transparency" in image.info:
                    # Paletted image with transparency
                    image = image.convert("RGBA")
                
                # Create white background
                background = Image.new("RGB", image.size, (255, 255, 255))
                
                # Paste the image onto the background
                if image.mode == "RGBA":
                    # RGBA mode - extract alpha channel
                    r, g, b, a = image.split()
                    background.paste(image, (0, 0), mask=a)
                elif image.mode == "LA":
                    # LA mode (grayscale with alpha)
                    # Convert to RGBA first
                    rgba_image = Image.new("RGBA", image.size)
                    rgba_image.paste(image, (0, 0))
                    r, g, b, a = rgba_image.split()
                    background.paste(rgba_image, (0, 0), mask=a)
                else:
                    # P mode or other modes
                    background.paste(image, (0, 0))
                
                image = background
            elif image.mode == "RGB":
                # Already RGB, no change needed
                pass
            else:
                # Convert other modes to RGB
                image = image.convert("RGB")
            
            st.sidebar.success(f"Converted to RGB: Mode={image.mode}")
        
        # For PNG output, ensure proper mode
        elif target_format == "PNG":
            if image.mode == "RGBA":
                # Keep RGBA for PNG if it has transparency
                pass
            elif image.mode in ("RGB", "P", "L"):
                # Convert to appropriate mode
                pass
            else:
                # Convert to RGBA or RGB
                if image.mode in ("LA", "PA"):
                    image = image.convert("RGBA")
                else:
                    image = image.convert("RGB")
        
        # Create output temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{target_lower}') as tmp:
            output_path = tmp.name
            
            # Save with optimized settings
            save_kwargs = {
                'format': pil_format,  # Use PIL format (JPEG instead of JPG)
                'optimize': True
            }
            
            # Add quality for JPG/JPEG
            if target_format in ["JPG", "JPEG"]:
                save_kwargs['quality'] = 95
                save_kwargs['progressive'] = True
            
            # Add compression for PNG
            elif target_format == "PNG":
                save_kwargs['compress_level'] = 6
            
            # Save the image
            image.save(output_path, **save_kwargs)
            
            # Verify the saved file
            try:
                verify_img = Image.open(output_path)
                st.sidebar.success(f"Saved successfully: {verify_img.format}, Size: {verify_img.size}")
                verify_img.close()
            except Exception as e:
                st.sidebar.warning(f"Could not verify saved image: {e}")
            
            return output_path

    except Exception as e:
        st.error(f"❌ Conversion failed: {str(e)}")
        import traceback
        st.sidebar.error(f"Detailed error: {traceback.format_exc()}")
        return None

# -------------------- Title --------------------
st.title("🗃️ Image Converter")
st.caption("Upload an image, choose a format, and download instantly")

# -------------------- Layout --------------------
col1, col2, col3 = st.columns(3, gap="medium")

# -------------------- Column 1 : Upload --------------------
with col1:
    st.subheader("📤 Upload Image")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Supported formats: PNG, JPG, JPEG",
        type=["png", "jpg", "jpeg"],
        key="file_uploader"
    )
    
    # If a new file is uploaded, store it in session state
    if uploaded_file is not None:
        # Store the uploaded file in session state
        st.session_state.uploaded_file = uploaded_file
        
        # Save the bytes to session state immediately
        st.session_state.image_bytes = uploaded_file.getvalue()
        
        # Show upload progress
        with st.spinner("Uploading..."):
            time.sleep(0.5)
        
        try:
            # Display original image from bytes
            image = Image.open(io.BytesIO(st.session_state.image_bytes))
            st.image(
                image,
                caption=f"Original: {uploaded_file.name}",
                use_container_width=True
            )
            st.caption(f"Original format: {image.format}, Mode: {image.mode}, Size: {image.size[0]}x{image.size[1]}")
            image.close()
        except Exception as e:
            st.error(f"Error displaying image: {e}")

# -------------------- Column 2 : Options --------------------
with col2:
    st.subheader("⚙️ Conversion Options")
    
    # Show the selected format with proper mapping
    target = st.radio(
        "Choose target format",
        ["JPG", "PNG", "JPEG"],
        horizontal=True,
        key="format_selector"
    )
    
    # Show format info
    if target in ["JPG", "JPEG"]:
        st.info(f"ℹ️ Will convert to JPEG format (PIL uses 'JPEG' for JPG files)")
        st.caption(f"Selected: {target} → PIL format: JPEG")
    else:
        st.info(f"ℹ️ Will convert to {target} format")

# -------------------- Column 3 : Output --------------------
with col3:
    st.subheader("📥 Output")
    
    # Check if we have an uploaded file in session state
    if st.session_state.get('image_bytes') and st.session_state.get('uploaded_file'):
        uploaded_file = st.session_state.uploaded_file
        
        # Show current status
        st.write(f"**Ready to convert:** {uploaded_file.name}")
        
        # Convert button
        convert_clicked = st.button("🔄 Convert Image", use_container_width=True, type="primary")
        
        if convert_clicked:
            with st.spinner(f"Converting to {target}..."):
                # Create temp file for input
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
                    tmp.write(st.session_state.image_bytes)
                    tmp_path = tmp.name
                    st.session_state.temp_files.append(tmp_path)
                    st.session_state.uploaded_file_path = tmp_path
                
                # Convert image
                output_path = convert_image(tmp_path, target)
                
                if output_path:
                    # Clean up previous converted file
                    if st.session_state.converted_file_path and st.session_state.converted_file_path != output_path:
                        try:
                            if os.path.exists(st.session_state.converted_file_path):
                                os.unlink(st.session_state.converted_file_path)
                                if st.session_state.converted_file_path in st.session_state.temp_files:
                                    st.session_state.temp_files.remove(st.session_state.converted_file_path)
                        except:
                            pass
                    
                    st.session_state.converted_file_path = output_path
                    st.session_state.temp_files.append(output_path)
                    
                    # Display converted image
                    try:
                        converted_img = Image.open(output_path)
                        st.image(
                            output_path,
                            caption=f"Converted to {target}",
                            use_container_width=True
                        )
                        st.success(f"✅ Successfully converted to {target}")
                        
                        # Show conversion details
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.caption(f"**Format:** {converted_img.format}")
                            st.caption(f"**Mode:** {converted_img.mode}")
                        with col_b:
                            st.caption(f"**Size:** {converted_img.size[0]}x{converted_img.size[1]}")
                            file_size = os.path.getsize(output_path) / 1024
                            st.caption(f"**File size:** {file_size:.1f} KB")
                        
                        converted_img.close()
                    except Exception as display_error:
                        st.error(f"Cannot display image: {display_error}")
                else:
                    st.error("Conversion failed. Check the sidebar for details.")
        
        # Download button (only show if conversion was successful)
        if st.session_state.converted_file_path and os.path.exists(st.session_state.converted_file_path):
            with open(st.session_state.converted_file_path, "rb") as f:
                # Use original filename with new extension
                original_name = Path(uploaded_file.name).stem
                download_ext = "jpg" if target in ["JPG", "JPEG"] else target.lower()
                download_name = f"{original_name}_converted.{download_ext}"
                
                st.download_button(
                    label=f"⬇️ Download as {target}",
                    data=f,
                    file_name=download_name,
                    mime=f"image/{download_ext}",
                    use_container_width=True,
                    type="secondary"
                )
    else:
        st.info("Upload an image to see the result here 👈")

# -------------------- Clear Button --------------------
if st.sidebar.button("🗑️ Clear All Files", type="secondary"):
    cleanup_temp_files()
    if st.session_state.uploaded_file_path:
        try:
            if os.path.exists(st.session_state.uploaded_file_path):
                os.unlink(st.session_state.uploaded_file_path)
        except:
            pass
    if st.session_state.converted_file_path:
        try:
            if os.path.exists(st.session_state.converted_file_path):
                os.unlink(st.session_state.converted_file_path)
        except:
            pass
    
    # Clear session state
    for key in ['uploaded_file', 'uploaded_file_path', 'converted_file_path', 'image_bytes']:
        if key in st.session_state:
            del st.session_state[key]
    
    st.session_state.temp_files = []
    st.rerun()

# -------------------- Debug Info --------------------
with st.sidebar.expander("🔍 Debug Information"):
    st.write("**Session State:**")
    for key in ['uploaded_file', 'uploaded_file_path', 'converted_file_path', 'image_bytes']:
        if key in st.session_state:
            st.write(f"- {key}: {'Set' if st.session_state[key] is not None else 'None'}")
    
    st.write(f"**Temp files:** {len(st.session_state.temp_files)}")
    
    # Show format mapping
    st.write("**Format Mapping:**")
    st.write("- User selects: JPG → PIL uses: JPEG")
    st.write("- User selects: JPEG → PIL uses: JPEG")
    st.write("- User selects: PNG → PIL uses: PNG")