import json
import os
import re
import math
import logging
import time
from typing import List, Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from crewai import Agent, Task, Crew, Process
from langchain_community.chat_models.litellm import ChatLiteLLM
from src.app.core.config import settings

logger = logging.getLogger(__name__)

# Configure LLM
api_key = settings.OPENAI_API_KEY
if not api_key:
    logger.warning("'OPENAI_API_KEY' not found in settings.")

# Using gpt-4o exactly as in POC
llm = ChatLiteLLM(model="openai/gpt-4o", api_key=api_key)


class AgentService:
    @staticmethod
    def load_json(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON from {filepath}: {e}")
            return None

    @staticmethod
    def save_json(data, filepath):
        output_dir = os.path.dirname(filepath)
        os.makedirs(output_dir, exist_ok=True)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.debug(f"JSON saved successfully to {filepath}")
        except Exception as e:
            logger.error(f"Error saving JSON to {filepath}: {e}")

    @staticmethod
    @retry(
        stop=stop_after_attempt(10),  # more attempts
        wait=wait_exponential(multiplier=2, min=10, max=120),  # longer wait
        # LiteLLM errors are generic or specific depending on version
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: logger.warning(
            f"LLM call failed (attempt {retry_state.attempt_number}), retrying in {retry_state.next_action.sleep}s...")
    )
    def _call_llm_with_retry(prompt: str):
        return llm.invoke(prompt)

    @staticmethod
    def get_llm_response_content(prompt: str) -> Optional[str]:
        try:
            logger.debug("Prompting LLM...")
            response = AgentService._call_llm_with_retry(prompt)
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)
        except Exception as e:
            logger.error(
                f"LLM Call Error after multiple retries: {e}", exc_info=True)
            return None

    # --- Preprocessing ---
    @classmethod
    def run_preprocessing(cls, input_path, output_folder, guideline_min_segments=10, guideline_max_segments=15, processing_batches=2):
        logger.info(f"--- Starting Pre-processing for {input_path} ---")
        input_data = cls.load_json(input_path)
        if input_data is None:
            logger.error(f"Failed to load input data from {input_path}")
            return False

        mini_segments_with_ids = []
        for i, item in enumerate(input_data):
            item['mini_seg_id'] = i
            mini_segments_with_ids.append(item)

        path_step1 = os.path.join(
            output_folder, "1-mini_segments_with_ids.json")
        cls.save_json(mini_segments_with_ids, path_step1)

        # Segmentation
        logger.info("Decision of segmentation points starts...")
        break_points = cls.get_batched_segmentation_plan(
            mini_segments_with_ids, guideline_min_segments, guideline_max_segments, processing_batches
        )
        if not break_points:
            logger.error("No break points generated. Segmentation failed.")
            return False

        logger.info(f"Merging into {len(break_points)} input segments...")
        merged_input_segments = cls.execute_merge_plan(
            mini_segments_with_ids, break_points)
        path_step2_data = os.path.join(
            output_folder, "2-merged_input_segments.json")
        path_step2_map = os.path.join(
            output_folder, "2a-merged_input_mapping.json")

        mapping = {
            seg['id']: f"{seg['mini_segments_used'][0]}-{seg['mini_segments_used'][-1]}"
            for seg in merged_input_segments
        }
        cls.save_json(merged_input_segments, path_step2_data)
        cls.save_json(mapping, path_step2_map)

        # Cleansing
        logger.info("Executing batched LLM cleansing process...")
        removal_data = cls.run_batched_llm_cleansing(
            merged_input_segments, processing_batches)
        if removal_data is None:
            logger.error(
                "Cleansing phase failed to return valid removal data.")
            return False

        logger.info(f"Identified {len(removal_data)} segments for removal.")
        path_removed_ids = os.path.join(output_folder, "removed_segments.json")
        cls.save_json(removal_data, path_removed_ids)

        path_step2b_cleansed = os.path.join(
            output_folder, "2b-merged_input_segments_cleared.json")
        cls.filter_and_save_cleansed(
            merged_input_segments, path_step2b_cleansed, removal_data)

        logger.info("Pre-processing phase complete.")
        return True

    @classmethod
    def get_batched_segmentation_plan(cls, mini_segments, min_guide, max_guide, num_batches):
        total_segments = len(mini_segments)
        if total_segments == 0:
            return []

        batch_size = math.ceil(total_segments / num_batches)
        all_break_points = []

        for i in range(num_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, total_segments)
            if start_idx >= total_segments:
                break

            current_batch = mini_segments[start_idx: end_idx]
            batch_breaks = cls.call_llm_for_segmentation(
                current_batch, min_guide, max_guide)
            all_break_points.extend(batch_breaks)

        all_break_points = sorted(list(set(all_break_points)))
        last_global_id = total_segments - 1
        if not all_break_points or (all_break_points and all_break_points[-1] < last_global_id):
            all_break_points.append(last_global_id)
        return all_break_points

    @classmethod
    def call_llm_for_segmentation(cls, batch, min_guide, max_guide):
        formatted_lines = []
        for item in batch:
            idx = item['mini_seg_id']
            text = item.get('text', '').replace(
                '"', "'").replace('\n', ' ').strip()
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
        response_str = cls.get_llm_response_content(prompt)
        if not response_str:
            return []
        try:
            json_match = re.search(r'\[.*\]', response_str, re.DOTALL)
            if json_match:
                breaks = json.loads(json_match.group(0))
                return [int(x) for x in breaks if isinstance(x, (int, str)) and str(x).isdigit()]
        except Exception:
            pass
        return []

    @classmethod
    def execute_merge_plan(cls, mini_segments, break_points):
        merged_segments = []
        current_start_idx = 0
        seg_counter = 1
        for break_idx in break_points:
            slice_end = break_idx + 1
            if slice_end > len(mini_segments):
                slice_end = len(mini_segments)
            chunk = mini_segments[current_start_idx: slice_end]
            if not chunk:
                current_start_idx = slice_end
                continue
            combined_text = " ".join([item.get('text', '') for item in chunk])
            start_time = chunk[0].get('start_second', 0.0)
            end_time = chunk[-1].get('end_second', 0.0)
            mini_seg_ids_used = [item['mini_seg_id'] for item in chunk]
            merged_segments.append({
                "id": f"seg_{seg_counter}",
                "text": combined_text,
                "start": start_time,
                "end": end_time,
                "mini_segments_used": mini_seg_ids_used
            })
            current_start_idx = slice_end
            seg_counter += 1
        return merged_segments

    @classmethod
    def run_batched_llm_cleansing(cls, merged_segments, num_batches):
        total_segments = len(merged_segments)
        if total_segments == 0:
            return []
        batch_size = math.ceil(total_segments / num_batches)
        all_removal_objects = []
        seen_ids = set()

        for i in range(num_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, total_segments)
            if start_idx >= total_segments:
                break
            current_batch = merged_segments[start_idx: end_idx]
            batch_removal_data = cls.call_llm_for_cleansing(current_batch)
            if batch_removal_data:
                for item in batch_removal_data:
                    if isinstance(item, dict) and 'id' in item and item['id'] not in seen_ids:
                        all_removal_objects.append(item)
                        seen_ids.add(item['id'])

        try:
            all_removal_objects.sort(key=lambda x: int(
                x['id'].split('_')[1]) if '_' in x['id'] else 0)
        except:
            pass
        return all_removal_objects

    @classmethod
    def call_llm_for_cleansing(cls, batch):
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
        response_str = cls.get_llm_response_content(prompt)
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
            logger.error(f"JSON Parsing Error in cleansing: {e}")
            return []

    @classmethod
    def filter_and_save_cleansed(cls, input_segments, output_path, removal_data):
        ids_to_remove = {item['id'] for item in removal_data}
        cleansed = [s for s in input_segments if s.get(
            'id') not in ids_to_remove]
        cls.save_json(cleansed, output_path)
        return True

    # --- CrewAI Pipeline ---
    @classmethod
    def run_crewai_pipeline(cls, output_folder):
        logger.info(f"Initiating CrewAI Pipeline in {output_folder}...")
        input_segments_path = os.path.join(
            output_folder, "2b-merged_input_segments_cleared.json")
        merged_path = os.path.join(output_folder, "4-conceptual_merges.json")
        final_path = os.path.join(output_folder, "5-final_results.json")

        input_data = cls.load_json(input_segments_path)
        if not input_data:
            logger.warning(
                "Agent input data empty or missing. Skipping CrewAI execution.")
            cls.save_json([], final_path)
            return True

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

        logger.info("Task 1: Conceptual Merging...")
        task_merge = Task(
            description=(
                f"TASK 3: CONCEPTUAL MERGING (HIGH VOLUME REQUIRED).\n"
                f"Take this list of filtered segments. They are transcripts for a video, so consider them a sequential script for the whole conversation. "
                f"Your goal is to identify and merge groups of **6 to 8 segments** to create standalone video scripts.\n\n"
                f"### *** PRIMARY DIRECTIVE: QUANTITY IS CRITICAL ***\n"
                f"You MUST generate **AT LEAST 8 to 10** merged video outputs. \n"
                f"Do NOT stop after finding 3 or 4 good matches. You must exhaustively scan the ENTIRE list of segments to extract every possible valid concept. "
                f"Failure to produce at least 8 outputs is a failed task.\n\n"
                f"**CRITICAL MERGING RULES:**\n"
                f"1. **STRICT SEGMENT LIMIT:** You are ONLY allowed to merge **6 to 8 segments per merged output**. "
                f"It is strictly forbidden to merge fewer than 6 or more than 8 segments. "
                f"This ensures the video length is 4–5 minutes.\n\n"
                f"2. **EXHAUSTIVE SEARCH STRATEGY:** "
                f"To achieve the 8-10 video target, you must look for concepts everywhere. "
                f"If a topic seems 'thin', use Non-Sequential Merging to find related segments from later in the text to build it up to the 6-8 segment requirement.\n\n"
                f"3. **PRESERVE SEGMENTS EXACTLY:** You MUST merge the *entire*, *exact* text content of each selected segment. "
                f"It is **STRICTLY FORBIDDEN** to remove, summarize, or alter any text *within* a segment. You must take the whole segment as-is.\n\n"
                f"4. **NON-SEQUENTIAL MERGING IS ALLOWED:** You MAY merge segments even if they are **not adjacent** or sequential in numbering, "
                f"as long as they belong to the **same conceptual topic**.\n\n"
                f"5. **NO CHANGES:** Do *not* add any new content, summaries, explanations, or modifications you should take the sgemnet as it is.\n\n"
                f"6. **BOUNDARY ANALYSIS (CRITICAL - NO SKIPPING):**\n"
                f"   Before finalizing your selection of 6-8 segments, you MUST perform this analysis:\n\n"
                f"   **A. START BOUNDARY CHECK:**\n"
                f"   - Look at the segment IMMEDIATELY BEFORE your chosen first segment.\n"
                f"   - Ask: Does my first segment depend on information, context, or references from that previous segment?\n"
                f"   - Ask: Does my first segment start mid-explanation, mid-example, or mid-reasoning?\n"
                f"   - If YES to either: You must INCLUDE that previous segment OR choose a different starting point.\n"
                f"   - Your first segment must introduce something NEW, not continue something already started.\n\n"
                f"   **B. END BOUNDARY CHECK:**\n"
                f"   - Look at the segment IMMEDIATELY AFTER your chosen last segment.\n"
                f"   - Ask: Does my last segment end with an incomplete thought that gets completed in the next segment?\n"
                f"   - Ask: Does my last segment promise an explanation/example that appears in the next segment?\n"
                f"   - If YES to either: You must INCLUDE that next segment OR choose a different ending point.\n"
                f"   - Your last segment must CLOSE a thought, not leave it hanging.\n\n"
                f"7. **SEQUENTIAL CONTEXT AWARENESS:**\n"
                f"   - When you skip segments (non-sequential merging), you MUST verify that the skipped segments don't contain critical context for your selected segments.\n"
                f"   - If segment 8 references 'this process' and you skipped segment 7 where 'this process' was explained, you cannot use segment 8.\n"
                f"   - Always trace backwards: for each segment you select, check if it depends on ANY previous segment you didn't include.\n\n"
                f"Input Filtered Segments:\n{json.dumps(input_data, indent=2)}\n\n"
                f"Your output MUST be a valid JSON list. Each object must have:\n"
                f"1. 'merged_text': The new smooth-flowing text, created by following the rules above.\n"
                f"2. 'start': The 'start' time of the *first* segment used.\n"
                f"3. 'end': The 'end' time of the *last* segment used.\n"
                f"4. 'big_segments_used': A list of the 'id' strings of all segments used.\n"
                f"5. 'vid_title': A short, descriptive title that you generate *based on the content* of the 'merged_text'.\n\n"
                f"6. 'reasoning': i want here the thinking of the llm why he chose these segmnets to be merged together , for example if he choose segmnets [3 5 8 9] i want reason for each segment and i want reason why he decided to jump and dont take [4 6 7]"
            ),
            agent=analyzer_agent,
            expected_output="A JSON string list of the conceptually merged segments. ONLY output the JSON list."
        )

        merged_data = cls.run_task_and_clean(
            analyzer_agent, task_merge, merged_path)
        if not merged_data:
            logger.error("Step 1 (Conceptual Merging) failed.")
            return False

        logger.info("Task 2: Final Processing...")
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
        cls.run_task_and_clean(analyzer_agent, task_finalize, final_path)

        logger.info("CrewAI processing successfully finished.")
        return True

    @classmethod
    def run_task_and_clean(cls, agent, task, output_path):
        logger.info(f"Kicking off task for {output_path}...")
        crew = Crew(agents=[agent], tasks=[task],
                    process=Process.sequential, verbose=False)
        result = crew.kickoff()
        raw = result.raw if hasattr(result, 'raw') else str(result)

        try:
            json_match = re.search(r'\[.*\]', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                cls.save_json(data, output_path)
                return data
            # Try to find JSON block code
            json_block = re.search(
                r'```json\s*(\[.*?\])\s*```', raw, re.DOTALL)
            if json_block:
                data = json.loads(json_block.group(1))
                cls.save_json(data, output_path)
                return data
        except Exception as e:
            logger.error(
                f"Failed to parse CrewAI output for {output_path}: {str(e)}", exc_info=True)
        return None

    # --- Postprocessing ---
    @classmethod
    def run_postprocessing(cls, output_folder):
        final_results_path = os.path.join(
            output_folder, "5-final_results.json")
        mapping_path = os.path.join(
            output_folder, "2a-merged_input_mapping.json")
        mapping_time_path = os.path.join(
            output_folder, "2-merged_input_segments.json")
        final_mapped_path = os.path.join(
            output_folder, "6-final_results_mapped.json")

        final_data = cls.load_json(final_results_path)
        mapping_data = cls.load_json(mapping_path)
        mapping_time_data = cls.load_json(mapping_time_path)

        if not final_data:
            cls.save_json([], final_mapped_path)
            return True

        # Timestamp map
        segment_timestamp_map = {
            s['id']: {'start': s['start'], 'end': s['end']}
            for s in mapping_time_data if 'id' in s
        }

        final_mapped = []
        for segment in final_data:
            new_seg = segment.copy()
            mapped_mini = []
            mapped_timestamps = []
            for big_id in segment.get("big_segments_used", []):
                # Look up in the map
                mini_range = mapping_data.get(big_id, "UNKNOWN_RANGE")
                mapped_mini.append(mini_range)

                # Look up in the timestamp map
                timestamp = segment_timestamp_map.get(
                    big_id, "UNKNOWN_TIMESTAMP")
                mapped_timestamps.append(timestamp)

            new_seg["mapped_mini_segment_ranges"] = mapped_mini
            new_seg["source_segment_timestamps"] = mapped_timestamps
            final_mapped.append(new_seg)

        cls.save_json(final_mapped, final_mapped_path)
        return True
