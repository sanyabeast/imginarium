import argparse
import yaml
import random
import uuid
import os
import json
import requests
import websocket
import time
from urllib.parse import urlparse
import lmstudio as lms
from pydantic import BaseModel

# Define schema for LM Studio response
class PromptSchema(BaseModel):
    prompt: str

# --- Configuration Loading ---
def load_config(config_path="config.yaml"):
    """Loads configuration from a YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        # Basic validation
        if not all(k in config for k in ['tags', 'lm_studio', 'comfy_ui', 'comfy_workflow']):
            raise ValueError("Config file missing required top-level keys.")
        if not config.get('comfy_workflow'):
             print("Warning: 'comfy_workflow' is not defined in config.yaml. ComfyUI generation will likely fail.")
        # Ensure output directory exists
        output_dir = config.get('comfy_ui', {}).get('output_directory', 'output_images')
        os.makedirs(output_dir, exist_ok=True)
        config['comfy_ui']['output_directory'] = output_dir # Store absolute path potentially
        # Generate client_id if not present
        if not config.get('comfy_ui', {}).get('client_id'):
            config['comfy_ui']['client_id'] = str(uuid.uuid4())

        return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file: {e}")
        exit(1)
    except ValueError as e:
        print(f"Error in configuration structure: {e}")
        exit(1)

# --- Tag Generation ---
def generate_tag_combinations(tags_config, num_combinations):
    """Generates random combinations of tags."""
    combinations = []
    tag_categories = list(tags_config.keys())

    if not tag_categories:
        print("Error: No tag categories defined in config.")
        return []

    for _ in range(num_combinations):
        selected_tags = []
        # Ensure at least one tag from each category if possible, handle empty categories
        possible_tags = 0
        for category in tag_categories:
            if tags_config[category]: # Check if category has tags
                 selected_tags.append(random.choice(tags_config[category]))
                 possible_tags +=1

        # Add more tags randomly if needed/possible (optional, could just stick to one per category)
        # This simple version just takes one tag per defined category.
        if not selected_tags:
             print(f"Warning: Could not select any tags for combination {_+1}. Check tag definitions in config.")
             continue # Skip if no tags could be selected

        combinations.append(", ".join(selected_tags))

    print(f"Generated {len(combinations)} tag combinations.")
    return combinations

# --- LM Studio Interaction ---
def generate_prompts_lm_studio(tag_combinations, lm_config, model_override=None):
    """Generates detailed prompts using LM Studio."""
    prompts = []
    prompt_template = lm_config.get('prompt_template')
    model_name = model_override or lm_config.get('model')

    if not prompt_template:
        print("Error: LM Studio 'prompt_template' not configured.")
        return []

    print(f"Generating {len(tag_combinations)} prompts using LM Studio...")
    print(f"Loading model: {model_name}")
    
    # Initialize LM Studio model
    try:
        model = lms.llm(model_name)
        print(f"Successfully loaded model: {model_name}")
    except Exception as e:
        print(f"Error loading LM Studio model: {e}")
        return []
    
    for i, tags in enumerate(tag_combinations):
        print(f"  Generating prompt {i+1}/{len(tag_combinations)} for tags: {tags}")
        
        try:
            # Create a prompt for the model
            system_prompt = f"""You are an expert prompt generator for AI image models.

Generate a detailed image prompt for a stock photo based on these tags: {tags}.
The prompt should be suitable for an AI image generator like Stable Diffusion.
Focus on visual details, composition, and lighting.

Generate only the prompt text, no explanations or additional text.
"""
            
            # Use the model to generate the prompt with the schema
            result = model.respond(system_prompt, response_format=PromptSchema)
            
            # Get the generated prompt from the parsed result
            generated_prompt = result.parsed["prompt"]
            prompts.append(generated_prompt)
            print(f"    Generated Prompt: {generated_prompt[:100]}...") # Print snippet
        except Exception as e:
            print(f"Error querying LM Studio: {e}")
            print("  Skipping prompt generation for this tag combination.")
        
        time.sleep(0.5) # Add a small delay between requests

    # Unload the model to free up GPU resources
    try:
        model.unload()
        print(f"Unloaded model: {model_name}")
    except Exception as e:
        print(f"Warning: Could not unload model: {e}")

    print(f"Successfully generated {len(prompts)} prompts.")
    return prompts

# --- ComfyUI Interaction (Adapted from example_comfy.py) ---
def queue_prompt(prompt_workflow, client_id, server_address):
    """Queues a prompt workflow to ComfyUI."""
    p = {"prompt": prompt_workflow, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    try:
        req = requests.post(f"http://{server_address}/prompt", data=data)
        req.raise_for_status()
        return req.json()
    except requests.exceptions.RequestException as e:
        print(f"Error queueing prompt with ComfyUI: {e}")
        return None

def get_image(filename, subfolder, folder_type, server_address):
    """Gets an image from ComfyUI server."""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urlparse(f"http://{server_address}/view")._replace(query=requests.compat.urlencode(data))
    try:
        response = requests.get(url_values.geturl())
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error getting image from ComfyUI: {e}")
        return None

def get_history(prompt_id, server_address):
    """Gets the execution history for a prompt from ComfyUI."""
    try:
        response = requests.get(f"http://{server_address}/history/{prompt_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting history from ComfyUI: {e}")
        return None

def get_images_from_websocket(ws, server_address, client_id, output_dir, prompt_id):
    """Listens to ComfyUI websocket for prompt execution status and retrieves images."""
    print(f"Waiting for ComfyUI results for prompt_id: {prompt_id}...")
    image_saved = False
    while True:
        try:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        print(f"  Execution finished for prompt_id: {prompt_id}.")
                        break # Execution is done
            else:
                continue # previews are binary data
        except websocket.WebSocketConnectionClosedException:
            print("WebSocket connection closed unexpectedly.")
            return False # Indicate failure
        except Exception as e:
            print(f"Error processing WebSocket message: {e}")
            # Decide if we should break or continue based on error
            break # Safer to break on unknown errors

    # Fetch history and retrieve image after execution finishes
    history = get_history(prompt_id, server_address)
    if not history or prompt_id not in history:
         print(f"  Could not find history for prompt_id: {prompt_id}")
         return False

    history_data = history[prompt_id]
    outputs = history_data.get('outputs', {})

    # Look for the SaveImage node in the outputs
    # We'll look for any node that has 'images' in its output
    image_saved = False
    for node_id, node_output in outputs.items():
        if 'images' in node_output:
            images_output = node_output['images']
            for image_data in images_output:
                if 'filename' in image_data:
                    filename = image_data['filename']
                    subfolder = image_data.get('subfolder', '')
                    img_type = image_data.get('type', 'output') # Usually 'output' or 'temp'

                    print(f"  Fetching image: {filename} (type: {img_type}, subfolder: '{subfolder}')")
                    image_content = get_image(filename, subfolder, img_type, server_address)
                    if image_content:
                        try:
                            image_filepath = os.path.join(output_dir, filename)
                            with open(image_filepath, 'wb') as f:
                                f.write(image_content)
                            print(f"  Image saved to: {image_filepath}")
                            image_saved = True
                        except IOError as e:
                            print(f"Error saving image {filename}: {e}")
                    else:
                        print(f"  Failed to retrieve image content for {filename}.")
                else:
                    print("  Warning: Image output data found but missing 'filename'.")

    if not image_saved:
        print("  No images found in the workflow output.")
        # Check if the workflow actually ran to completion or failed mid-way
        status_data = history_data.get('status', {})
        if status_data.get('status_str') == 'error':
             print(f"  ComfyUI workflow execution failed: {status_data.get('exception_message', 'Unknown error')}")

    return image_saved

def generate_images_comfyui(prompts, config):
    """Generates images for each prompt using ComfyUI."""
    server_address = config['comfy_ui'].get('server_address')
    client_id = config['comfy_ui'].get('client_id')
    output_dir = config['comfy_ui'].get('output_directory')
    workflow_str = config.get('comfy_workflow') # This is now a string, not a JSON object
    
    # Default values for workflow placeholders
    default_negative_prompt = "text, watermark, signature, blurry, distorted, low resolution, poorly drawn, bad anatomy, deformed, disfigured, out of frame, cropped"
    default_steps = 20
    
    if not server_address or not client_id or not workflow_str:
        print("Error: ComfyUI 'server_address', 'client_id', or 'comfy_workflow' not configured correctly.")
        return

    print(f"Connecting to ComfyUI WebSocket at ws://{server_address}/ws?clientId={client_id}")
    ws = None
    try:
        ws = websocket.WebSocket()
        ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
    except Exception as e:
        print(f"Error connecting to ComfyUI WebSocket: {e}")
        return

    print(f"Starting image generation for {len(prompts)} prompts using ComfyUI...")
    images_generated = 0

    for i, prompt_text in enumerate(prompts):
        print(f"""---
Processing prompt {i+1}/{len(prompts)}: {prompt_text[:100]}...
---""")

        # Create a copy of the workflow string for this prompt
        current_workflow_str = workflow_str
        
        # Generate a random seed for this prompt
        random_seed = random.randint(1, 2147483647)
        
        # Replace placeholders in the workflow string
        # Note: We're directly substituting the values, not as JSON strings
        current_workflow_str = current_workflow_str.replace('"{PROMPT}"', json.dumps(prompt_text))
        current_workflow_str = current_workflow_str.replace('"{NEGATIVE_PROMPT}"', json.dumps(default_negative_prompt))
        current_workflow_str = current_workflow_str.replace('{SEED}', str(random_seed))
        current_workflow_str = current_workflow_str.replace('{STEPS}', str(default_steps))
        
        # Parse the string into a JSON object
        try:
            current_workflow = json.loads(current_workflow_str)
        except json.JSONDecodeError as e:
            print(f"Error parsing workflow JSON: {e}")
            print("Skipping this prompt.")
            continue
        
        print(f"  Using seed: {random_seed}, steps: {default_steps}")
        print(f"  Negative prompt: {default_negative_prompt[:50]}...")

        # Queue the modified workflow
        queued_data = queue_prompt(current_workflow, client_id, server_address)
        if queued_data and 'prompt_id' in queued_data:
            prompt_id = queued_data['prompt_id']
            print(f"  Queued prompt with ID: {prompt_id}")
            # Wait for results and get image via WebSocket
            if get_images_from_websocket(ws, server_address, client_id, output_dir, prompt_id):
                 images_generated += 1
            else:
                print(f"  Failed to get image for prompt_id {prompt_id}.")
        else:
            print("  Failed to queue prompt in ComfyUI.")

        time.sleep(1) # Small delay between queuing prompts

    ws.close()
    print(f"Finished ComfyUI processing. {images_generated}/{len(prompts)} images generated successfully.")


# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate stock-like images using LM Studio and ComfyUI.")
    parser.add_argument("-n", "--num-images", type=int, default=5, help="Number of images to generate.")
    parser.add_argument("-m", "--model", type=str, help="LM Studio model to use (overrides config)")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to the configuration file.")
    args = parser.parse_args()

    print(f"Starting stock image generation for {args.num_images} images...")

    # 1. Load Configuration
    print(f"Loading configuration from '{args.config}'...")
    config = load_config(args.config)
    if not config:
        exit(1)

    # 2. Generate Tag Combinations
    print("Generating tag combinations...")
    tag_combinations = generate_tag_combinations(config.get('tags', {}), args.num_images)
    if not tag_combinations:
        print("No tag combinations generated, exiting.")
        exit(1)

    # 3. Generate Prompts using LM Studio
    print("Generating prompts via LM Studio...")
    detailed_prompts = generate_prompts_lm_studio(tag_combinations, config.get('lm_studio', {}), args.model)
    if not detailed_prompts:
        print("No prompts generated by LM Studio, exiting.")
        exit(1)

    # 4. Generate Images using ComfyUI
    print("Generating images via ComfyUI...")
    generate_images_comfyui(detailed_prompts, config)

    print("--- Script Finished ---")
