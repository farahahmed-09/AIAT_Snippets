import json
import os
import re
import math
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from langchain_community.chat_models.litellm import ChatLiteLLM

# 1. Load Environment Variables
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    print("❌ ERROR: 'GEMINI_API_KEY' not found in environment variables.")

# 2. Configure LLM
llm = ChatLiteLLM(model="gemini/gemini-2.5-pro", api_key=gemini_api_key)

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def load_json(filepath):
    """Loads a JSON file from the given filepath."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}")
        return None

def save_json(data, filepath):
    """Saves data to a JSON file at the given filepath."""
    output_dir = os.path.dirname(filepath)
    os.makedirs(output_dir, exist_ok=True)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Successfully saved: {filepath}")
    except IOError as e:
        print(f"Error saving JSON file at {filepath}: {e}")

def get_llm_response_content(prompt: str) -> Optional[str]:
    """Helper to safely get text content from LLM response."""
    try:
        response = llm.invoke(prompt)
        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            return str(response)
    except Exception as e:
        print(f"LLM Call Error: {e}")
        return None

# ==========================================
# 4. STEP 1: PREPROCESSING LOGIC
# ==========================================

def run_preprocessing(
    input_path,
    output_folder,
    guideline_min_segments=10, # Default mapped from SEGMENTS_PER_CHUNK logic if needed
    guideline_max_segments=15,
    processing_batches=2
):
    """
    Refactored Pipeline with Reasoning Extraction:
    1. Load Data & Assign IDs.
    2. BATCHED Segmentation: Split -> Plan -> Merge.
    3. BATCHED Cleansing: Split -> Get Bad IDs + Reasoning -> Remove.
    """
    print(f"--- Starting Task 1: Pre-processing (Batched Strategy: {processing_batches} loops) ---")

    # --- Step 1: Load input and add sequential 'mini_seg_id' ---
    input_data = load_json(input_path)
    if input_data is None:
        return False

    mini_segments_with_ids = []
    for i, item in enumerate(input_data):
        item['mini_seg_id'] = i
        mini_segments_with_ids.append(item)

    path_step1 = os.path.join(output_folder, "1-mini_segments_with_ids.json")
    save_json(mini_segments_with_ids, path_step1)

    # --- Step 2: Batched Dynamic Merging ---
    print(f"--- Starting Step 2: Segmentation (Splitting into {processing_batches} batches) ---")

    break_points = get_batched_segmentation_plan(
        mini_segments_with_ids,
        guideline_min_segments,
        guideline_max_segments,
        num_batches=processing_batches
    )

    if not break_points:
        print("CRITICAL ERROR: Could not generate segmentation plan. Aborting.")
        return False

    merged_input_segments = execute_merge_plan(mini_segments_with_ids, break_points)

    # Save Step 2 results
    path_step2_data = os.path.join(output_folder, "2-merged_input_segments.json")
    path_step2_map = os.path.join(output_folder, "2a-merged_input_mapping.json")

    # Mapping for debugging
    mapping = {
        seg['id']: f"{seg['mini_segments_used'][0]}-{seg['mini_segments_used'][-1]}"
        for seg in merged_input_segments
    }
    save_json(merged_input_segments, path_step2_data)
    save_json(mapping, path_step2_map)

    # --- Step 3: Batched Cleansing (UPDATED) ---
    print(f"\n--- Starting Step 3: Cleansing (Splitting into {processing_batches} batches) ---")

    # 3.1 Get the Master Removal List (Now containing Reasons)
    removal_data = run_batched_llm_cleansing(merged_input_segments, num_batches=processing_batches)

    if removal_data is None:
        print("Error during LLM cleansing step. Halting.")
        return False

    # --- Save the removed IDs AND Reasoning to file ---
    path_removed_ids = os.path.join(output_folder, "removed_segments.json")
    save_json(removal_data, path_removed_ids)
    print(f"Saved list of {len(removal_data)} removed segments with reasoning to {path_removed_ids}")

    # 3.2 Filter and Save
    path_step2b_cleansed = os.path.join(output_folder, "2b-merged_input_segments_cleared.json")

    success = filter_and_save_cleansed(
        input_segments_data=merged_input_segments,
        output_path=path_step2b_cleansed,
        removal_data=removal_data
    )

    print("\n--- Pre-processing Finished (Batched Logic Applied) ---")
    return True

# --- Preprocessing Helpers ---

def get_batched_segmentation_plan(mini_segments: List[dict], min_guide: int, max_guide: int, num_batches: int) -> List[int]:
    total_segments = len(mini_segments)
    if total_segments == 0: return []
    
    batch_size = math.ceil(total_segments / num_batches)
    all_break_points = []

    print(f"Total items: {total_segments}. Batch size: ~{batch_size}")

    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, total_segments)
        if start_idx >= total_segments:
            break

        current_batch = mini_segments[start_idx : end_idx]
        print(f"Processing Segmentation Batch {i+1}/{num_batches} (IDs {start_idx} to {end_idx-1})...")
        batch_breaks = call_llm_for_segmentation(current_batch, min_guide, max_guide)
        all_break_points.extend(batch_breaks)

    all_break_points = sorted(list(set(all_break_points)))
    last_global_id = total_segments - 1
    if not all_break_points or (all_break_points and all_break_points[-1] < last_global_id):
        all_break_points.append(last_global_id)

    return all_break_points

def call_llm_for_segmentation(batch: List[dict], min_guide: int, max_guide: int) -> List[int]:
    formatted_lines = []
    for item in batch:
        idx = item['mini_seg_id']
        text = item.get('text', '').replace('"', "'").replace('\n', ' ').strip()
        formatted_lines.append(f"[{idx}] {text}")

    batch_text = "\n".join(formatted_lines)
    prompt = (
        f"You are an expert content editor. Below is a PART of a larger transcript.\n"
        f"Your task is to group these lines into coherent segments.\n"
        f"Pass over the text and decide where each segment should END.\n\n"
        f"GUIDELINES:\n"
        f"1. Ideal segment length: {min_guide} to {max_guide} lines.\n"
        f"2. Prioritize logical flow (completing a thought/sentence) over strict counts.\n"
        f"3. Return ONLY the IDs of the lines where a segment ENDS.\n\n"
        f"TRANSCRIPT PART:\n"
        f"--- START ---\n"
        f"{batch_text}\n"
        f"--- END ---\n\n"
        f"OUTPUT:\n"
        f"Return ONLY a valid JSON list of integers (e.g. [105, 130, 155])."
    )

    response_str = get_llm_response_content(prompt)
    if not response_str: return []

    try:
        json_match = re.search(r'\[.*\]', response_str, re.DOTALL)
        if json_match:
            breaks = json.loads(json_match.group(0))
            return [int(x) for x in breaks if isinstance(x, (int, str)) and str(x).isdigit()]
        return []
    except Exception:
        return []

def execute_merge_plan(mini_segments: List[dict], break_points: List[int]) -> List[dict]:
    merged_segments = []
    current_start_idx = 0
    seg_counter = 1

    for break_idx in break_points:
        slice_end = break_idx + 1
        if slice_end > len(mini_segments):
            slice_end = len(mini_segments)

        chunk = mini_segments[current_start_idx : slice_end]
        if not chunk:
            current_start_idx = slice_end
            continue

        combined_text = " ".join([item.get('text', '') for item in chunk])
        start_time = chunk[0].get('start_second', 0.0)
        end_time = chunk[-1].get('end_second', 0.0)
        mini_seg_ids_used = [item['mini_seg_id'] for item in chunk]
        big_seg_id = f"seg_{seg_counter}"

        merged_segments.append({
            "id": big_seg_id,
            "text": combined_text,
            "start": start_time,
            "end": end_time,
            "mini_segments_used": mini_seg_ids_used
        })

        current_start_idx = slice_end
        seg_counter += 1

    return merged_segments

def run_batched_llm_cleansing(merged_segments: List[dict], num_batches: int) -> List[Dict[str, str]]:
    total_segments = len(merged_segments)
    if total_segments == 0: return []
    batch_size = math.ceil(total_segments / num_batches)

    all_removal_objects = []
    seen_ids = set() 

    print(f"Total merged segments: {total_segments}. Cleansing Batch size: ~{batch_size}")

    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, total_segments)

        if start_idx >= total_segments:
            break

        current_batch = merged_segments[start_idx : end_idx]
        print(f"Processing Cleansing Batch {i+1}/{num_batches}...")

        batch_removal_data = call_llm_for_cleansing(current_batch)

        if batch_removal_data:
            for item in batch_removal_data:
                if isinstance(item, dict) and 'id' in item and item['id'] not in seen_ids:
                    all_removal_objects.append(item)
                    seen_ids.add(item['id'])

    try:
        all_removal_objects.sort(key=lambda x: int(x['id'].split('_')[1]) if '_' in x['id'] else 0)
    except:
        pass 

    print(f"--- Total segments identified for removal: {len(all_removal_objects)} ---")
    return all_removal_objects

def call_llm_for_cleansing(batch: List[dict]) -> List[Dict[str, str]]:
    formatted_text_list = []
    for seg in batch:
        s_id = seg['id']
        s_text = seg['text'].replace('"', "'").replace('\n', ' ')
        formatted_text_list.append(f"({s_id}) \"{s_text}\"")

    full_text_block = "\n".join(formatted_text_list)

    prompt = (
        "You are a professional video editor and transcript analyst.\n"
        "Your task is to identify segments to CUT (remove) to create a clean lecture.\n\n"
        "### CRITICAL INSTRUCTION ON QUESTIONS (THE 'SELF-Q&A' RULE) ###\n"
        "The instructor often uses a 'Self-Questioning' persona. They ask a question to introduce a topic and then ANSWER it themselves.\n"
        "You generally CANNOT identify the speaker by name, so you must analyze the CONTEXT:\n\n"
        "TYPE A: INSTRUCTOR QUESTIONS (MUST KEEP):\n"
        "- The speaker asks: \"So, what is marketing?\" and immediately follows with \"Marketing is the study of...\"\n"
        "- The speaker asks: \"Why does this matter?\" and immediately follows with \"It matters because...\"\n"
        "- RULE: If the question acts as a HEADLINE or TOPIC INTRO, KEEP IT.\n\n"
        # "TYPE B: STUDENT/INTERRUPTION QUESTIONS (MUST REMOVE):\n"
        # "- Questions that signal confusion: \"Sir, I didn't understand that.\"\n"
        # "- Questions that halt the flow: \"Can you repeat the last part?\"\n"
        # "- Questions requiring the instructor to acknowledge an outsider: \"Yes, you have a question?\"\n"
        # "- RULE: If the question disrupts the lesson or asks for repetition, REMOVE IT.\n\n"
        # "### REMOVAL CRITERIA ###\n"
        # "REMOVE a segment ONLY if it contains:\n"
        # "1. Student/Audience Interruptions (e.g., 'Sir...', 'Excuse me...', 'Is this on the test?').\n"
        # "2. Technical checks (e.g., 'Is my screen shared?', 'Can you hear me?').\n"
        # "3. Explicit off-topic chatter (e.g., 'The weather is nice today'—unless it's an analogy).\n\n"

        "TYPE B: STUDENT INTERACTIONS & CLARIFICATIONS (CONDITIONAL):"
        "- Context-Aware Filtering: Do not blindly remove all student questions. You must evaluate the instructor's response to determine value."

        "### RETENTION CRITERIA (WHEN TO KEEP) ###"
        "KEEP the question and answer pair ONLY IF the instructor's response provides:"
        "1. Elaboration: The instructor explains the concept in a new way or adds depth not present in the main lecture flow."
        "2. Illustration: The instructor provides a specific example, analogy, or case study to clarify the point."
        "3. Correction: The instructor corrects a common misconception that adds educational value."
        "- RULE: If the interaction deepens understanding, treat it as part of the core lesson content."

        "### REMOVAL CRITERIA (WHEN TO DELETE) ###"
        "REMOVE the segment ONLY if it falls into these categories:"
        "1. Pure Repetition: The question asks to repeat information ('Can you say that again?', 'I missed the last part') and the instructor simply repeats the same words."
        "2. Logistical/Administrative: Questions regarding exams, timing, or grades ('Is this on the test?', 'Will we get a break?')."
        "3. Technical/Environmental: Issues with audio, visuals, or surroundings ('Is the screen shared?', 'The font is too small')."
        "4. Empty Affirmations: Short interactions that do not add content (Student: 'Okay, I see.' Instructor: 'Good.')."
        "5. CRITICAL TECHNICAL CLEANUP: Strictly filter out any segments that appear to have audio glitches or looping text (e.g., consecutive repeated words like 'going to going to going to'). These are invalid data points and must be discarded."
        "### GOLDEN RULE ###\n"
        "If you are unsure if a question is from the Instructor or a Student, ASSUME IT IS THE INSTRUCTOR and KEEP IT. Only remove if you are 100% sure it is an interruption.\n\n"
        "TRANSCRIPT BATCH:\n"
        "--- START ---\n"
        f"{full_text_block}\n"
        "--- END ---\n\n"
        "OUTPUT FORMAT:\n"
        "- Return ONLY a valid JSON array of objects.\n"
        "- Example: [{\"id\": \"seg_12\", \"reason\": \"Student asking for repetition\"}]\n"
        "- If nothing should be removed, return: []"
    )

    response_str = get_llm_response_content(prompt)
    if not response_str:
        return []

    try:
        json_match = re.search(r'\[.*\]', response_str, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            valid_items = []
            for item in data:
                if isinstance(item, dict) and 'id' in item:
                    if 'reason' not in item:
                        item['reason'] = "No specific reason provided by LLM"
                    valid_items.append(item)
            return valid_items
        return []
    except Exception as e:
        print(f"JSON Parsing Error in cleansing: {e}")
        return []

def filter_and_save_cleansed(input_segments_data: List[dict], output_path: str, removal_data: List[Dict[str, str]]):
    ids_to_remove_set = {item['id'] for item in removal_data}
    cleansed_segments = []
    removed_count = 0

    for seg in input_segments_data:
        if seg.get('id') not in ids_to_remove_set:
            cleansed_segments.append(seg)
        else:
            removed_count += 1

    save_json(cleansed_segments, output_path)
    print(f"Removed {removed_count} segments. Saved {len(cleansed_segments)} segments to {output_path}")
    return True


# ==========================================
# 5. STEP 2: AGENT PIPELINE (CrewAI)
# ==========================================

def run_task_and_clean(agent, task, output_path):
    """
    Helper function: Runs a single task, extracts the clean JSON from its
    raw output, and saves it.
    """
    print(f"\n--- Running Task: {task.description[:50]}... ---")

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False
    )
    crew_result = crew.kickoff()

    if not crew_result or not (hasattr(crew_result, 'raw') and crew_result.raw):
        print(f"Error: Task failed to produce raw output.")
        return None

    raw_output_string = crew_result.raw
    print("Raw output from agent (snippet):")
    print(raw_output_string[:400] + "...")

    try:
        start_index = raw_output_string.find('[')
        end_index = raw_output_string.rfind(']')

        if start_index == -1 or end_index == -1 or end_index <= start_index:
            # Fallback: Check for code block
            json_block_match = re.search(r'```json\s*(\[.*?\])\s*```', raw_output_string, re.DOTALL)
            if json_block_match:
                json_str = json_block_match.group(1)
                print("Found JSON in code block.")
            else:
                print("Error: Could not find valid JSON list '[]' in agent's output.")
                with open(output_path + ".ERROR.txt", "w", encoding='utf-8') as f:
                    f.write(raw_output_string)
                return None
        else:
            json_str = raw_output_string[start_index : end_index + 1]
            print("Found JSON by slicing [ and ].")

        parsed_json = json.loads(json_str)
        save_json(parsed_json, output_path)
        print(f"Successfully cleaned and saved JSON to: {output_path}")
        return parsed_json
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode extracted JSON. {e}")
        with open(output_path + ".ERROR.txt", "w", encoding='utf-8') as f:
            f.write(raw_output_string)
        return None

def run_crewai_pipeline(output_folder):
    """
    Runs the sequential CrewAI tasks (Merge, Finalize)
    """
    print("--- Starting Tasks: CrewAI Pipeline ---")

    # Define File Paths
    input_segments_path = os.path.join(output_folder, "2b-merged_input_segments_cleared.json")
    merged_path = os.path.join(output_folder, "4-conceptual_merges.json")
    final_path = os.path.join(output_folder, "5-final_results.json")

    # Load initial data
    input_segments_data = load_json(input_segments_path)

    if input_segments_data is None:
        print(f"Cannot start CrewAI pipeline: '{os.path.basename(input_segments_path)}' not found.")
        return False

    if not input_segments_data:
        print(f"Warning: Input file is empty. Skipping CrewAI pipeline.")
        save_json([], merged_path)
        save_json([], final_path)
        return True 

    # --- The Agent ---
    analyzer_agent = Agent(
        role='Instructional Designer and Script Strategist',
        goal=(
            'Extract singular, powerful learning modules from a long, unstructured lecture. '
            'Create self-contained scripts that teach exactly one concept per video.'
        ),
        backstory=(
            "You are an expert instructional designer who converts messy webinars into structured micro-learning courses. "
            "You have a talent for identifying the 'start' and 'end' of a specific topic within a rambling speech. "
            "Your goal is to find clusters of segments that explain a concept fully (Problem -> Explanation -> Solution) "
            "so that a viewer can watch a 4-minute clip and learn something new without needing the rest of the video."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

    # --- Task: Conceptual Merging ---
    task_merge = Task(
    description=(
        f"TASK 3: CONCEPTUAL MERGING.\n"
        f"Take this list of filtered segments. They are transcripts for a video, so consider them a sequential script for the whole conversation. "
        f"Your goal is to identify and merge groups of **4 to 5 segments ONLY** that are strongly related to the **SAME 'concept' or 'idea'**.\n\n"

        f"**CRITICAL MERGING RULES:**\n"

        f"1. **STRICT SEGMENT LIMIT (CRITICAL):** You are ONLY allowed to merge **4 to 5 segments per merged output**. "
        f"⚠️ It is strictly forbidden to merge fewer than 4 or more than 5 segments. "
        f"This rule is critical to ensure the final output stays within **400–800 words** and guarantees a **3–5 minute video length**.\n\n"

        f"2. **MINIMUM OUTPUT REQUIREMENT (CRITICAL):** You MUST generate **at least 5 to 10 merged video outputs**. "
        f"⚠️ You should search on all possible segments to be merged to together \n\n"

        f"3. **PRESERVE SEGMENTS EXACTLY:** You MUST merge the *entire*, *exact* text content of each selected segment. "
        f"It is **STRICTLY FORBIDDEN** to remove, summarize, or alter any text *within* a segment. You must take the whole segment as-is.\n\n"

        f"4. **NON-SEQUENTIAL MERGING IS ALLOWED:** You MAY merge segments even if they are **not adjacent** or sequential in numbering, "
        f"as long as they belong to the **same conceptual topic**.\n\n"

        f"5. **NO CHANGES:** Do *not* add any new content, summaries, explanations, or modifications you should take the sgemnet as it is.\n\n"

        f"Input Filtered Segments:\n{json.dumps(input_segments_data, indent=2)}\n\n"

        f"Your output MUST be a valid JSON list. Each object must have:\n"
        f"1. 'merged_text': The new smooth-flowing text, created by following the rules above.\n"
        f"2. 'start': The 'start' time of the *first* segment used.\n"
        f"3. 'end': The 'end' time of the *last* segment used.\n"
        f"4. 'big_segments_used': A list of the 'id' strings of all segments used.\n"
        f"5. 'vid_title': A short, descriptive title that you generate *based on the content* of the 'merged_text'.\n\n"
        f"6. 'reasoning': i want here the thinking of the llm why he chose these segmnets to be merged together , for example if he choose segmnets [3 5 8 9] i want reason for each segment and i want reason why he decided to jump and dont take [4 6 7]"

        f"Example output: [{{"
        f"'merged_text': '(This is the first segment.) ... In addition to this, ... (This is a related segment.) ...', "
        f"'start': 10.0, "
        f"'end': 75.0, "
        f"'big_segments_used': ['seg_1', 'seg_5', 'seg_7', 'seg_8'], "
        f"'vid_title': 'A Title Based on the Content'"
        f"'reasoning': i decided to remove segments .... because of ... , and leave segments ... because of ..."
        f"}}]"
    ),
    agent=analyzer_agent,
    expected_output="A JSON string list of the conceptually merged segments. ONLY output the JSON list."
    )

    merged_data = run_task_and_clean(analyzer_agent, task_merge, merged_path)
    if not merged_data:
        print("Halting: Task (Merging) failed or produced no data.")
        if merged_data == []:
            save_json([], final_path)
            return True
        return False

    # --- Task: Final Filtering ---
    task_finalize = Task(
        description=(
            f"TASK: FINAL FILTERING.\n"
            f"Take this list of conceptually merged segments. Perform a final quality check.\n"
            f"Make sure each merged segment can form a 3-5 min video (approx 400-800 words).\n"
            f"ONLY KEEP segments that are 'self-contained'. Discard segments that sound like intros or outros.\n\n"
            f"Input Merged Segments:\n{json.dumps(merged_data, indent=2)}\n\n"
            f"Your output MUST be a valid JSON list containing only the final segments."
        ),
        agent=analyzer_agent,
        expected_output="A JSON string list of the final, self-contained segments. ONLY output the JSON list."
    )

    final_data = run_task_and_clean(analyzer_agent, task_finalize, final_path)
    if not final_data:
        print("Warning: Finalize task produced no data.")

    print("\n--- CrewAI Pipeline Finished ---")
    return True


# ==========================================
# 6. STEP 3: POSTPROCESSING
# ==========================================

def run_postprocessing(output_folder):
    """
    Maps the 'big_segments_used' in the final results back to the
    original 'mini_segment' ranges from the pre-processing map.
    """
    print("--- Starting Task 5: Post-processing (New Mapping) ---")

    # File paths
    final_results_path = os.path.join(output_folder, "5-final_results.json")
    mapping_path = os.path.join(output_folder, "2a-merged_input_mapping.json")
    mapping_time_path = os.path.join(output_folder, "2-merged_input_segments.json")
    final_mapped_path = os.path.join(output_folder, "6-final_results_mapped.json")

    # Load data
    final_results_data = load_json(final_results_path)
    mapping_data = load_json(mapping_path)
    mapping_time_data = load_json(mapping_time_path)

    if final_results_data is None:
        print("Error: Could not load '5-final_results.json'.")
        return False
    if mapping_data is None:
        print("Error: Could not load '2a-merged_input_mapping.json'.")
        return False
    if mapping_time_data is None:
        print(f"Error: Could not load '{os.path.basename(mapping_time_path)}'.")
        return False

    # Handle case where no final results were produced
    if not final_results_data:
        print("No final results to post-process. Saving an empty mapped file.")
        save_json([], final_mapped_path)
        return True

    final_mapped_results = []

    # Create the timestamp lookup map
    segment_timestamp_map = {}
    for seg in mapping_time_data:
        seg_id = seg.get("id")
        if seg_id:
            segment_timestamp_map[seg_id] = {
                "start": seg.get("start"),
                "end": seg.get("end")
            }

    for segment in final_results_data:
        big_segments_used = segment.get("big_segments_used", [])
        mapped_mini_ranges = []
        mapped_timestamps = []

        for big_seg_id in big_segments_used:
            # Look up "seg_1" in the map
            mini_range = mapping_data.get(big_seg_id, "UNKNOWN_RANGE")
            mapped_mini_ranges.append(mini_range)

            # Look up "seg_1" in the timestamp map
            timestamp = segment_timestamp_map.get(big_seg_id, "UNKNOWN_TIMESTAMP")
            mapped_timestamps.append(timestamp)

        new_segment_data = segment.copy()
        new_segment_data["mapped_mini_segment_ranges"] = mapped_mini_ranges
        new_segment_data["source_segment_timestamps"] = mapped_timestamps

        final_mapped_results.append(new_segment_data)

    save_json(final_mapped_results, final_mapped_path)
    print("--- Post-processing Finished ---")
    return True