import argparse
import yaml
import random
import uuid
import os
import json
import time
import requests
import websocket
from urllib.parse import urlparse
import lmstudio as lms
from pydantic import BaseModel
from db import ImageDatabase  # Import the database module
from PIL import Image, PngImagePlugin
import sys
from datetime import datetime

# Define schema for LM Studio response
class PromptSchema(BaseModel):
    prompt: str

# --- Fancy Logging Helpers ---
def print_header(title):
    """Print a fancy header with emojis."""
    print(f"\n{'='*60}")
    print(f"✨✨  {title}  ✨✨")
    print(f"{'='*60}")

def print_subheader(title, emoji="🔹"):
    """Print a fancy subheader with emoji."""
    print(f"\n{emoji} {title} {emoji}")

def print_step(step_num, total_steps, description, emoji="🚀"):
    """Print a step with progress indicator."""
    progress = f"[{step_num}/{total_steps}]"
    print(f"{emoji} {progress} {description}")

def print_success(message, emoji="✅"):
    """Print a success message."""
    print(f"{emoji} {message}")

def print_warning(message, emoji="⚠️"):
    """Print a warning message."""
    print(f"{emoji} {message}")

def print_error(message, emoji="❌"):
    """Print an error message."""
    print(f"{emoji} {message}")

def print_info(message, emoji="ℹ️"):
    """Print an info message."""
    print(f"{emoji} {message}")

def print_progress_bar(iteration, total, prefix='', suffix='', length=30, fill='█'):
    """Print a progress bar."""
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
    if iteration == total: 
        print()

# --- Utility Functions ---
def tags_to_filename(tags_str):
    """Convert a tags string to a snake_case filename."""
    # Extract just the tag values (not the categories)
    tag_values = []
    for tag_item in tags_str.split(', '):
        if ':' in tag_item:
            category, value = tag_item.split(':', 1)
            tag_values.append(value)
        else:
            tag_values.append(tag_item)
    
    # Convert to lowercase and replace spaces with underscores
    filename = '_'.join(tag_values).lower().replace(' ', '_')
    
    # Add a random component to prevent overwrites
    timestamp = int(time.time())
    random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
    filename = f"{filename}_{timestamp}_{random_str}"
    
    # Limit length to avoid excessively long filenames
    if len(filename) > 100:
        # Preserve the random component at the end
        random_part = f"_{timestamp}_{random_str}"
        max_base_length = 100 - len(random_part)
        filename = f"{filename[:max_base_length]}{random_part}"
    
    return filename

# --- Configuration Loading ---
def load_config(config_path="config.yaml"):
    """Loads configuration from a YAML file."""
    try:
        print_info(f"Loading configuration from '{config_path}'...")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        # Basic validation
        if not all(k in config for k in ['tags', 'lm_studio', 'comfy_ui']):
            raise ValueError("Config file missing required top-level keys.")
        
        # Remove workflow warning since we now load workflows from files
        # Ensure output directory exists
        output_dir = config.get('comfy_ui', {}).get('output_directory', 'output_images')
        os.makedirs(output_dir, exist_ok=True)
        config['comfy_ui']['output_directory'] = output_dir # Store absolute path potentially
        # Generate client_id if not present
        if not config.get('comfy_ui', {}).get('client_id'):
            config['comfy_ui']['client_id'] = str(uuid.uuid4())
        
        print_success("Configuration loaded successfully! 🎉")
        return config
    except FileNotFoundError:
        print_error(f"Configuration file '{config_path}' not found.")
        exit(1)
    except yaml.YAMLError as e:
        print_error(f"Error parsing configuration file: {e}")
        exit(1)
    except ValueError as e:
        print_error(f"Error in configuration structure: {e}")
        exit(1)

# --- Tag Generation ---
def generate_tag_combinations(tags_config, num_combinations):
    """Generates random combinations of tags from all categories."""
    print_subheader("Generating Tag Combinations", "🏷️")
    combinations = []
    tag_categories = list(tags_config.keys())

    if not tag_categories:
        print_error("No tag categories defined in config.")
        return []
    
    # Define which categories to include in each combination
    # We want to ensure a good mix of different elements
    required_categories = ["subject", "action", "setting", "mood", "style"]
    optional_categories = ["lighting", "camera_angle"]
    
    # Verify that required categories exist in the config
    missing_categories = [cat for cat in required_categories if cat not in tag_categories]
    if missing_categories:
        print_warning(f"Some required tag categories are missing from config: {missing_categories}")
        # Adjust required categories to only include those that exist
        required_categories = [cat for cat in required_categories if cat in tag_categories]
    
    # Adjust optional categories to only include those that exist
    optional_categories = [cat for cat in optional_categories if cat in tag_categories]

    print_info(f"Using categories: {', '.join(tag_categories)}")
    print_info(f"Required: {', '.join(required_categories)}")
    print_info(f"Optional: {', '.join(optional_categories)}")

    for i in range(num_combinations):
        print_progress_bar(i+1, num_combinations, prefix='Progress:', suffix='Complete', length=40)
        selected_tags = []
        
        # Add one tag from each required category
        for category in required_categories:
            if category in tags_config and tags_config[category]:
                selected_tags.append(f"{category}:{random.choice(tags_config[category])}")
            else:
                print_warning(f"Required category '{category}' is empty or not defined.")
        
        # Randomly decide whether to include each optional category (50% chance)
        for category in optional_categories:
            if category in tags_config and tags_config[category] and random.random() > 0.5:
                selected_tags.append(f"{category}:{random.choice(tags_config[category])}")
        
        if not selected_tags:
            print_warning(f"Could not select any tags for combination {i+1}. Check tag definitions in config.")
            continue # Skip if no tags could be selected

        combinations.append(", ".join(selected_tags))

    print_success(f"Generated {len(combinations)} tag combinations! 🎯")
    return combinations

# --- LM Studio Interaction ---
def generate_prompts_lm_studio(tag_combinations, lm_config, model_override=None):
    """Generates detailed prompts using LM Studio."""
    print_subheader("Generating Prompts with LM Studio", "🧠")
    prompts = []
    prompt_template = lm_config.get('prompt_template')
    model_name = model_override or lm_config.get('model')

    if not prompt_template:
        print_error("LM Studio 'prompt_template' not configured.")
        return []

    print_info(f"Loading model: {model_name}")
    
    # Initialize LM Studio model
    try:
        # Generate a random seed for LM Studio
        lm_seed = random.randint(1, 2147483647)
        print_info(f"Using LM Studio seed: {lm_seed}")
        
        model = lms.llm(model_name, config={
            "seed": lm_seed,
            "temperature": 0.8,           # ↑ more randomness & word variety
    "top_p": 0.95,                # ↑ allows broader probability mass
    "top_k": 100,                 # ↑ allows sampling from more potential words
        })
        print_success(f"Successfully loaded model: {model_name}")
    except Exception as e:
        print_error(f"Error loading LM Studio model: {e}")
        return []
    
    for i, tags in enumerate(tag_combinations):
        print_step(i+1, len(tag_combinations), f"Processing tags: {tags}", "🔄")
        
        try:
            # Create a prompt for the model
            prompt = f"""You are an expert prompt generator for AI image models.

Generate a detailed image prompt for a stock photo based on these tags: {tags}.
The prompt should be suitable for an AI image generator like Stable Diffusion.
Focus on visual details, composition, and lighting.

Generate only the prompt text, no explanations or additional text.
"""
            
            # Use the model to generate the prompt with the schema
            result = model.respond(prompt, response_format=PromptSchema)
            
            # Get the generated prompt from the parsed result
            generated_prompt = result.parsed["prompt"]
            prompts.append(generated_prompt)
            print_info(f"Generated: {generated_prompt[:100]}...") # Print snippet
        except Exception as e:
            print_error(f"Error querying LM Studio: {e}")
            print_warning("Skipping prompt generation for this tag combination.")
        
        time.sleep(0.5) # Add a small delay between requests

    # Unload the model to free up GPU resources
    try:
        model.unload()
        print_info(f"Unloaded model: {model_name}")
    except Exception as e:
        print_warning(f"Could not unload model: {e}")

    print_success(f"Successfully generated {len(prompts)} prompts! 📝")
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
        print_error(f"Error queueing prompt with ComfyUI: {e}")
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
        print_error(f"Error getting image from ComfyUI: {e}")
        return None

def get_history(prompt_id, server_address):
    """Gets the execution history for a prompt from ComfyUI."""
    try:
        response = requests.get(f"http://{server_address}/history/{prompt_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print_error(f"Error getting history from ComfyUI: {e}")
        return None

def get_images_from_websocket(ws, server_address, client_id, output_dir, prompt_id):
    """Listens to ComfyUI websocket for prompt execution status and retrieves images."""
    print_info(f"Waiting for ComfyUI to generate image...")
    image_saved = False
    while True:
        try:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        print_success(f"Generation complete!")
                        break # Execution is done
            else:
                continue # previews are binary data
        except websocket.WebSocketConnectionClosedException:
            print_error("WebSocket connection closed unexpectedly.")
            return False # Indicate failure
        except Exception as e:
            print_error(f"Error processing WebSocket message: {e}")
            # Decide if we should break or continue based on error
            break # Safer to break on unknown errors

    # Fetch history and retrieve image after execution finishes
    history = get_history(prompt_id, server_address)
    if not history or prompt_id not in history:
         print_error(f"Could not find history for prompt_id: {prompt_id}")
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

                    print_info(f"Saving image...")
                    image_content = get_image(filename, subfolder, img_type, server_address)
                    if image_content:
                        try:
                            image_filepath = os.path.join(output_dir, filename)
                            with open(image_filepath, 'wb') as f:
                                f.write(image_content)
                            print_success(f"Image saved to: {image_filepath}")
                            image_saved = True
                        except IOError as e:
                            print_error(f"Error saving image {filename}: {e}")
                    else:
                        print_error(f"Failed to retrieve image content for {filename}.")
                else:
                    print_warning("Image output data found but missing 'filename'.")

    if not image_saved:
        print_warning("No images found in the workflow output.")
        # Check if the workflow actually ran to completion or failed mid-way
        status_data = history_data.get('status', {})
        if status_data.get('status_str') == 'error':
             print_error(f"ComfyUI workflow execution failed: {status_data.get('exception_message', 'Unknown error')}")

    return image_saved

def generate_images_comfyui(prompts, config, tag_combinations=None, db=None, workflow_name="flux_dev"):
    """Generates images for each prompt using ComfyUI."""
    print_subheader("Generating Images with ComfyUI", "🖼️")
    server_address = config['comfy_ui'].get('server_address')
    client_id = config['comfy_ui'].get('client_id')
    output_dir = config['comfy_ui'].get('output_directory')
    
    print_info(f"Saving images to: {output_dir}")
    
    # Load workflow from file
    workflow_path = os.path.join("workflows", workflow_name)
    try:
        with open(workflow_path, 'r') as f:
            workflow_str = f.read()
        print_info(f"Using workflow: {workflow_name}")
    except FileNotFoundError:
        print_error(f"Workflow file not found: {workflow_path}")
        print_info(f"Make sure the workflow file exists in the 'workflows' directory")
        return
    except Exception as e:
        print_error(f"Error loading workflow: {e}")
        return
    
    # Get parameters from config with defaults if not specified
    steps = config['comfy_ui'].get('steps', 20)
    width = config['comfy_ui'].get('width', 1024)
    height = config['comfy_ui'].get('height', 1024)
    
    # Default values for workflow placeholders
    default_negative_prompt = "text, watermark, signature, blurry, distorted, low resolution, poorly drawn, bad anatomy, deformed, disfigured, out of frame, cropped"
    
    if not server_address or not client_id or not workflow_str:
        print_error("ComfyUI 'server_address', 'client_id', or 'workflow' not configured correctly.")
        return

    print_info(f"Connecting to ComfyUI WebSocket at ws://{server_address}/ws?clientId={client_id}")
    ws = None
    try:
        ws = websocket.WebSocket()
        ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
        print_success("Connected to ComfyUI WebSocket!")
    except Exception as e:
        print_error(f"Error connecting to ComfyUI WebSocket: {e}")
        return

    print_info(f"Starting image generation for {len(prompts)} prompts")
    print_info(f"Using parameters: width={width}, height={height}, steps={steps}")
    images_generated = 0

    for i, prompt_text in enumerate(prompts):
        print_step(i+1, len(prompts), "Processing prompt", "🎨")
        # Print the full prompt
        print_info(f"Prompt: {prompt_text}")

        # Create a copy of the workflow string for this prompt
        current_workflow_str = workflow_str
        
        # Generate a random seed for this prompt
        random_seed = random.randint(1, 2147483647)
        
        # Create a custom filename based on tags if available
        custom_filename = f"image_{i+1}"
        if tag_combinations and i < len(tag_combinations):
            custom_filename = tags_to_filename(tag_combinations[i])
            # Truncate the displayed filename if it's too long
            display_filename = custom_filename
            if len(display_filename) > 40:
                display_filename = display_filename[:20] + "..." + display_filename[-17:]
            print_info(f"Using filename based on tags: {display_filename}")
        
        # Add workflow name as prefix to the filename
        custom_filename = f"{workflow_name}_{custom_filename}"
        print_info(f"Final filename with workflow prefix: {custom_filename}")
        
        # Replace placeholders in the workflow string
        # Note: We're directly substituting the values, not as JSON strings
        # Use replace() with no count limit to replace all occurrences of each placeholder
        current_workflow_str = current_workflow_str.replace('"{PROMPT}"', json.dumps(prompt_text))
        current_workflow_str = current_workflow_str.replace('"{NEGATIVE_PROMPT}"', json.dumps(default_negative_prompt))
        current_workflow_str = current_workflow_str.replace('{NEGATIVE_PROMPT}', default_negative_prompt)  # For direct text fields
        current_workflow_str = current_workflow_str.replace('{PROMPT}', prompt_text)  # For direct text fields
        current_workflow_str = current_workflow_str.replace('{SEED}', str(random_seed))
        current_workflow_str = current_workflow_str.replace('{STEPS}', str(steps))
        current_workflow_str = current_workflow_str.replace('{WIDTH}', str(width))
        current_workflow_str = current_workflow_str.replace('{HEIGHT}', str(height))
        
        # Replace the filename placeholder with our custom filename
        # This works with any workflow that uses the {FILENAME_PREFIX} placeholder
        current_workflow_str = current_workflow_str.replace('"{FILENAME_PREFIX}"', json.dumps(custom_filename))
        
        # Parse the string into a JSON object
        try:
            current_workflow = json.loads(current_workflow_str)
        except json.JSONDecodeError as e:
            print_error(f"Error parsing workflow JSON: {e}")
            print_warning("Skipping this prompt.")
            continue
        
        print_info(f"Using seed: {random_seed}, steps: {steps}, dimensions: {width}x{height}")
        print_info(f"Negative prompt: {default_negative_prompt[:50]}...")

        # Queue the modified workflow
        queued_data = queue_prompt(current_workflow, client_id, server_address)
        if queued_data and 'prompt_id' in queued_data:
            prompt_id = queued_data['prompt_id']
            print_info(f"Starting generation...")
            # Wait for results and get image via WebSocket
            if get_images_from_websocket(ws, server_address, client_id, output_dir, prompt_id):
                 images_generated += 1
                 print_success(f"Successfully generated image {images_generated}! 🎉")
                 
                 # Save to database if provided
                 if db and db.is_connected():
                     # Get the actual filename that was saved
                     filename = f"{custom_filename}_00001_.png"  # Default format from ComfyUI
                     file_path = os.path.join(output_dir, filename)
                     
                     # Parse tags into a structured format
                     tags_data = {}
                     tag_string = ""
                     if tag_combinations and i < len(tag_combinations):
                         # Convert the tag string into a structured object
                         tag_string = tag_combinations[i]
                         for tag_item in tag_string.split(", "):
                             if ":" in tag_item:
                                 category, value = tag_item.split(":", 1)
                                 tags_data[category] = value
                     
                     # Store in database
                     db.add_image(
                         filename=filename,
                         tags=tags_data,  # Store as structured object instead of string
                         prompt=prompt_text,
                         seed=random_seed,
                         steps=steps,
                         width=width,
                         height=height,
                         workflow=workflow_name,  # Add workflow name
                         ratio=round(width/height, 2)  # Calculate and store aspect ratio
                     )
                     print_info(f"Added image to database: {filename}")
                     
                     # Add metadata to the PNG image
                     metadata = {
                         "Prompt": prompt_text,
                         "Tags": tag_string,
                         "Seed": random_seed,
                         "Steps": steps,
                         "Width": width,
                         "Height": height,
                         "Workflow": workflow_name,
                         "Ratio": round(width/height, 2),
                         "Generator": "Stock Image Generator",
                         "Created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                     }
                     add_metadata_to_image(file_path, metadata)
            else:
                print_error(f"Failed to get image for prompt_id {prompt_id}.")
        else:
            print_error("Failed to queue prompt in ComfyUI.")

        time.sleep(1) # Small delay between queuing prompts

    ws.close()
    print_success(f"Finished ComfyUI processing. {images_generated}/{len(prompts)} images generated successfully! 🎉")

def add_metadata_to_image(image_path, metadata):
    """
    Add metadata to a PNG image using text chunks.
    
    Args:
        image_path (str): Path to the PNG image
        metadata (dict): Dictionary of metadata to add to the image
    """
    try:
        # Check if file exists and is a PNG
        if not os.path.exists(image_path):
            print_error(f"Image not found: {image_path}")
            return False
            
        if not image_path.lower().endswith('.png'):
            print_warning(f"Metadata can only be added to PNG images: {image_path}")
            return False
        
        # Open the image
        img = Image.open(image_path)
        
        # Create a PngInfo object
        meta = PngImagePlugin.PngInfo()
        
        # Add metadata as text chunks
        for key, value in metadata.items():
            if value is not None:
                # Convert any non-string values to strings
                meta.add_text(key, str(value))
        
        # Save the image with metadata
        img.save(image_path, "PNG", pnginfo=meta)
        print_info(f"Added metadata to image: {image_path}")
        return True
    except Exception as e:
        print_error(f"Error adding metadata to image: {e}")
        return False

def read_metadata_from_image(image_path):
    """
    Read metadata from a PNG image.
    
    Args:
        image_path (str): Path to the PNG image
        
    Returns:
        dict: Dictionary of metadata from the image, or empty dict if no metadata or error
    """
    try:
        # Check if file exists and is a PNG
        if not os.path.exists(image_path):
            print_error(f"Image not found: {image_path}")
            return {}
            
        if not image_path.lower().endswith('.png'):
            print_warning(f"Metadata can only be read from PNG images: {image_path}")
            return {}
        
        # Open the image
        img = Image.open(image_path)
        
        # Get metadata
        metadata = {}
        for key, value in img.info.items():
            # Skip internal PIL keys
            if key.startswith('pil_'):
                continue
            metadata[key] = value
        
        return metadata
    except Exception as e:
        print_error(f"Error reading metadata from image: {e}")
        return {}

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate stock-like images using LM Studio and ComfyUI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 5 images with the flux_dev workflow
  python generate.py -n 5 -w flux_dev
  
  # Use a specific LM Studio model
  python generate.py -n 3 -m "llama-3-8b-instruct" -w flux_dev
  
  # Specify custom image dimensions
  python generate.py -n 2 -w flux_dev -d 1920x1080
  
  # Override the number of steps for generation
  python generate.py -n 2 -w flux_dev -s 30
  
  # Combine parameters
  python generate.py -n 5 -m "gemma-3-4b-it" -w flux_dev -d 1024x1024 -s 40
"""
    )
    parser.add_argument("-n", "--num-images", type=int, default=5, help="Number of images to generate.")
    parser.add_argument("-m", "--model", type=str, help="LM Studio model to use (overrides config)")
    parser.add_argument("-w", "--workflow", type=str, required=True, help="Workflow to use from the workflows directory")
    parser.add_argument("-d", "--dimensions", type=str, help="Image dimensions in format WIDTHxHEIGHT (e.g., 1920x1080)")
    parser.add_argument("-s", "--steps", type=int, help="Number of diffusion steps for image generation (higher = better quality but slower)")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to the configuration file.")
    args = parser.parse_args()

    print_header(f"🌟 Stock Image Generator 🌟")
    print_info(f"Generating {args.num_images} images")
    if args.model:
        print_info(f"Using model override: {args.model}")
    
    # Check if workflow file exists
    workflow_path = os.path.join("workflows", args.workflow)
    if not os.path.exists(workflow_path):
        print_error(f"Workflow file not found: {workflow_path}")
        print_info(f"Make sure the workflow file exists in the 'workflows' directory")
        exit(1)
    else:
        print_info(f"Using workflow: {args.workflow}")

    try:
        # 1. Load Configuration
        config = load_config(args.config)
        if not config:
            exit(1)

        # 2. Generate Tag Combinations
        tag_combinations = generate_tag_combinations(config.get('tags', {}), args.num_images)
        if not tag_combinations:
            print_error("No tag combinations generated, exiting.")
            exit(1)

        # 3. Generate Prompts using LM Studio
        detailed_prompts = generate_prompts_lm_studio(tag_combinations, config.get('lm_studio', {}), args.model)
        if not detailed_prompts:
            print_error("No prompts generated by LM Studio, exiting.")
            exit(1)

        # 4. Generate Images using ComfyUI
        db = ImageDatabase() # Initialize database connection with config file settings
        if args.dimensions:
            try:
                if 'x' not in args.dimensions:
                    raise ValueError("Size must be in format WIDTHxHEIGHT (e.g., 1920x1080)")
                width, height = map(int, args.dimensions.split('x'))
                if width <= 0 or height <= 0:
                    raise ValueError("Width and height must be positive integers")
                print_info(f"Overriding image dimensions: {width}x{height}")
                config['comfy_ui']['width'] = width
                config['comfy_ui']['height'] = height
            except ValueError as e:
                print_error(f"Invalid size format: {e}")
                sys.exit(1)
        if args.steps:
            print_info(f"Overriding steps count: {args.steps}")
            config['comfy_ui']['steps'] = args.steps
        generate_images_comfyui(detailed_prompts, config, tag_combinations, db, args.workflow)
        
        print_header("✨ All Done! ✨")
        print_success("Check your output directory for the generated images!")
        print_info("Thank you for using Stock Image Generator! 🙏")
        
        # Close database connection
        if db and db.is_connected():
            db.close()
            
    except KeyboardInterrupt:
        print("\n")
        print_warning("Process interrupted by user (Ctrl+C)")
        print_info("Exiting gracefully...")
        # You could add any cleanup code here if needed
        print_info("Goodbye! 👋")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        print_info("Exiting with error...")
        sys.exit(1)
