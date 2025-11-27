import streamlit as st
import requests
import os
import json

# Configuration
API_BASE = "http://127.0.0.1:8000"
CONFIG_FILE_PATH = r"D:\AIAT_Snippets\user_profile\config.json"
TRANSCRIPT_PATH = r"D:\AIAT_Snippets\input_data\transcript_timestamped.json"
FINAL_JSON_PATH = r"D:\AIAT_Snippets\output_data\Agent_pipeline_output_files\6-final_results_mapped.json"

st.set_page_config(page_title="AIAT Configuration", layout="wide")

st.title("🔎 AIAT : Snippets Generation")

# --- Tabs for better UI organization ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["1. Configuration", "2. Transcription", "3. Processing", "4. Trim & Concat", "5. Final UI Attachment"])

# ==========================================
# TAB 1: PARAMETER CONFIGURATION
# ==========================================
with tab1:
    st.header("Step 1: Input Parameters")

    with st.form("config_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name", placeholder="e.g., John Doe")
            title = st.text_input("Title", placeholder="e.g., Senior Analyst")
        
        with col2:
            video_link = st.text_input("Video Link (Direct URL)", placeholder="https://example.com/video.mp4")

        st.subheader("Media Uploads")
        profile_picture = st.file_uploader("Profile Picture", type=["jpg", "png", "jpeg"])
        intro_video = st.file_uploader("Intro Video", type=["mp4", "mov", "avi"])
        background_picture = st.file_uploader("Background Picture", type=["jpg", "png", "jpeg"])

        submitted = st.form_submit_button("Save Configuration")

        if submitted:
            if not all([name, title, video_link, profile_picture, intro_video, background_picture]):
                st.error("⚠️ Please fill in all fields and upload all files.")
            else:
                with st.spinner("Saving data..."):
                    try:
                        files = {
                            "profile_picture": (profile_picture.name, profile_picture, profile_picture.type),
                            "intro_video": (intro_video.name, intro_video, intro_video.type),
                            "background_picture": (background_picture.name, background_picture, background_picture.type),
                        }
                        data = {"video_link": video_link, "name": name, "title": title}

                        response = requests.post(f"{API_BASE}/configure", data=data, files=files)

                        if response.status_code == 200:
                            st.success("✅ Configuration saved successfully!")
                            st.info("You can now proceed to the Transcription tab.")
                        else:
                            st.error(f"❌ Error: {response.text}")
                    except Exception as e:
                        st.error(f"❌ Connection Error: {e}")

# ==========================================
# TAB 2: TRANSCRIPT GENERATION
# ==========================================
with tab2:
    st.header("Step 2: Transcribe Video")
    
    config_exists = os.path.exists(CONFIG_FILE_PATH)
    
    if config_exists:
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                saved_config = json.load(f)
            
            st.info("ℹ️ This will download the video and run the Whisper AI model.")
            
            if st.button("Generate Transcript", type="primary"):
                with st.status("Transcribing...", expanded=True) as status:
                    st.write("📡 Transcribing Video, please wait this may take a while...")
                    try:
                        response = requests.post(f"{API_BASE}/transcribe", timeout=1200) 
                        
                        if response.status_code == 200:
                            result = response.json()
                            status.update(label="✅ Transcription Complete!", state="complete", expanded=False)
                            st.success("Transcription generated successfully!")
                            st.write(f"**Transcript saved at:** `{result.get('transcript_path')}`")
                            st.info("You can now proceed to the Processing tab.")
                        else:
                            status.update(label="❌ Error", state="error")
                            st.error(f"Backend Error: {response.text}")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
        except Exception as e:
             st.error(f"Error reading config file: {e}")
    else:
        st.warning("⚠️ No configuration found.")

# ==========================================
# TAB 3: AI AGENT PROCESSING (UPDATED)
# ==========================================
with tab3:
    st.header("Step 3: Run AI Agent Pipeline")
    st.markdown("This step runs the pre-processing, CrewAI agents, and post-processing logic.")

    transcript_ready = os.path.exists(TRANSCRIPT_PATH)

    if transcript_ready:
        st.success(f"✅ Transcript found")
    else:
        st.warning(f"⚠️ Transcript not found at: `{TRANSCRIPT_PATH}`. Please check the file path.")

    # --- Initialize Session State for this tab ---
    if "pipeline_data" not in st.session_state:
        st.session_state.pipeline_data = None
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False

    if transcript_ready:
        # Only show the RUN button if we don't have data yet, or if user wants to re-run
        if st.button("🚀 Execute Agent Pipeline", type="primary"):
            with st.status("Running AI Pipeline ", expanded=True) as status:
                st.write("⚙️ Please wait this may take a while..")
                try:
                    response = requests.post(f"{API_BASE}/processing", timeout=3600)

                    if response.status_code == 200:
                        res_data = response.json()
                        status.update(label="✅ Pipeline Finished!", state="complete", expanded=False)
                        
                        st.success("Pipeline Execution Successful!")
                        st.write(f"**Output Folder:** `{res_data.get('output_folder')}`")
                        
                        # Save result to session state so it persists
                        st.session_state.pipeline_data = res_data.get("data")
                        st.session_state.edit_mode = False # Reset edit mode on new run
                    else:
                        status.update(label="❌ Pipeline Failed", state="error")
                        st.error(f"Backend Error: {response.text}")

                except requests.exceptions.ReadTimeout:
                     st.error("❌ Request timed out. The agents are taking too long. Check your backend console.")
                except Exception as e:
                    st.error(f"❌ Connection Error: {e}")

        st.divider()

        # --- DISPLAY & EDIT LOGIC ---
        if st.session_state.pipeline_data:
            st.subheader("Final Results")
            
            # Toggle Button logic
            col_view, col_edit = st.columns([0.8, 0.2])
            with col_view:
                st.info("Review the generated snippets below.")
            with col_edit:
                if st.button("✏️ Edit JSON"):
                    st.session_state.edit_mode = not st.session_state.edit_mode

            if st.session_state.edit_mode:
                st.warning("⚠️ You are in Edit Mode. Be careful with JSON syntax.")
                
                # Convert JSON object to formatted string for the text area
                json_str = json.dumps(st.session_state.pipeline_data, indent=4)
                
                # Text Area for editing
                edited_json_str = st.text_area(
                    "Edit Raw JSON", 
                    value=json_str, 
                    height=500
                )

                if st.button("💾 Save Changes"):
                    try:
                        # 1. Validate JSON syntax locally
                        updated_json_obj = json.loads(edited_json_str)
                        
                        # 2. Send to Backend to overwrite file
                        save_response = requests.post(f"{API_BASE}/update_json_results", json=updated_json_obj)
                        
                        if save_response.status_code == 200:
                            st.success("✅ Changes saved to file successfully!")
                            # Update session state with new data
                            st.session_state.pipeline_data = updated_json_obj
                            st.session_state.edit_mode = False # Exit edit mode
                            st.rerun() # Refresh UI
                        else:
                            st.error(f"Failed to save: {save_response.text}")

                    except json.JSONDecodeError as e:
                        st.error(f"❌ Invalid JSON Syntax: {e}")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

            else:
                # View Only Mode
                st.json(st.session_state.pipeline_data)


# ==========================================
# TAB 4: TRIM AND CONCAT
# ==========================================


with tab4:
    st.header("Step 4: Generate Video Clips")
    st.markdown("This step uses the JSON from Step 3 to cut the original video and concatenate the selected snippets.")
    
    # Check if necessary files exist
    json_ready = os.path.exists(FINAL_JSON_PATH)
    
    if json_ready:
        st.success("✅ Snippets script found.")
        
        # Initialize session state for videos if not present
        if "generated_videos_path" not in st.session_state:
            st.session_state.generated_videos_path = None

        if st.button("✂️ Trim & Concat Videos", type="primary"):
            with st.status("Processing Videos...", expanded=True) as status:
                st.write("🎞️ Extracting clips and merging... please wait.")
                try:
                    # Timeout set to 30 minutes just in case
                    response = requests.post(f"{API_BASE}/trim_concat", timeout=1800)

                    if response.status_code == 200:
                        res_data = response.json()
                        output_folder = res_data.get('output_folder')
                        
                        # Store in session state so videos persist
                        st.session_state.generated_videos_path = output_folder
                        
                        status.update(label="✅ Video Generation Complete!", state="complete", expanded=False)
                        st.success(f"Videos generated successfully!")
                    else:
                        status.update(label="❌ Error", state="error")
                        st.error(f"Backend Error: {response.text}")
                        
                except Exception as e:
                     st.error(f"❌ Connection Error: {e}")

        # --- DISPLAY VIDEOS SECTION ---
        # We check session state so this runs even after the button click event finishes
        if st.session_state.generated_videos_path and os.path.exists(st.session_state.generated_videos_path):
            
            output_folder = st.session_state.generated_videos_path
            
            # Find all MP4 files in the directory
            video_files = [f for f in os.listdir(output_folder) if f.endswith(".mp4")]
            
            if video_files:
                st.divider()
                st.subheader(f"📺 Generated Snippets ({len(video_files)})")
                
                # Create a grid layout (2 videos per row)
                cols = st.columns(2)
                
                for idx, video_file in enumerate(video_files):
                    file_path = os.path.join(output_folder, video_file)
                    
                    # Display in alternating columns
                    with cols[idx % 2]:
                        st.markdown(f"**🎬 {video_file}**")
                        # st.video accepts a local file path
                        st.video(file_path)
            else:
                st.warning(f"Process finished, but no MP4 files were found in: {output_folder}")

    else:
        st.warning(f"⚠️ Processed JSON not found at: `{FINAL_JSON_PATH}`. Please complete Step 3 first.")

# ==========================================
# TAB 5: FINAL UI ATTACHMENT
# ==========================================
with tab5:
    st.header("Step 5: Apply Branding (UI Attachment)")
    st.markdown("This step generates custom intros, overlays the video on your background, and merges them.")

    # Define the default path where Step 4 outputs files (Matches your API configuration)
    DEFAULT_RAW_VIDEOS_PATH = r"D:\AIAT_Snippets\output_data\raw_videos_snippets"

    # --- CHECK IF RAW CLIPS EXIST ---
    step4_done = False
    
    # 1. Check Session State (If Step 4 was just run)
    if st.session_state.get("generated_videos_path") and os.path.exists(st.session_state.generated_videos_path):
        step4_done = True
    
    # 2. Fallback: Check the hardcoded directory on disk
    elif os.path.exists(DEFAULT_RAW_VIDEOS_PATH) and len(os.listdir(DEFAULT_RAW_VIDEOS_PATH)) > 0:
        step4_done = True
        # Update session state so the UI knows where to look
        st.session_state.generated_videos_path = DEFAULT_RAW_VIDEOS_PATH
        st.info(f"ℹ️ Found existing raw snippets.")

    # --- CHECK CONFIG ---
    config_ready = os.path.exists(CONFIG_FILE_PATH)

    if step4_done and config_ready:
        st.success("✅ Raw Snippets and User Configurations are ready.")
        
        if "branded_videos_path" not in st.session_state:
            st.session_state.branded_videos_path = None

        if st.button("🎨 Apply UI & Branding", type="primary"):
            with st.status("Generating Final Branded Videos...", expanded=True) as status:
                st.write("1️⃣ Creating Intro Clips.")
                st.write("2️⃣ Stitching Backgrounds.")
                st.write("3️⃣ Concatenating Final Output.")
                try:
                    # Long timeout as video processing is heavy
                    response = requests.post(f"{API_BASE}/add_ui_components", timeout=3600) 

                    if response.status_code == 200:
                        res_data = response.json()
                        output_folder = res_data.get('output_folder')
                        st.session_state.branded_videos_path = output_folder
                        
                        status.update(label="✅ Branding Complete!", state="complete", expanded=False)
                        st.success("Final videos created successfully!")
                    else:
                        status.update(label="❌ Error", state="error")
                        st.error(f"Backend Error: {response.text}")
                except Exception as e:
                    st.error(f"❌ Connection Error: {e}")

        # Display Final Videos
        if st.session_state.branded_videos_path and os.path.exists(st.session_state.branded_videos_path):
            final_folder = st.session_state.branded_videos_path
            final_files = [f for f in os.listdir(final_folder) if f.endswith(".mp4")]
            
            if final_files:
                st.divider()
                st.subheader(f"🚀 Final Branded Videos ({len(final_files)})")
                
                cols = st.columns(2)
                for idx, video_file in enumerate(final_files):
                    file_path = os.path.join(final_folder, video_file)
                    with cols[idx % 2]:
                        st.markdown(f"**🎬 {video_file}**")
                        st.video(file_path)
            else:
                st.warning("No files found in output folder.")

    else:
        if not config_ready:
            st.warning("⚠️ Configuration file missing. Please go to Step 1.")
        if not step4_done:
            st.warning(f"⚠️ No raw snippets found in session or at `{DEFAULT_RAW_VIDEOS_PATH}`. Please complete Step 4 first.")