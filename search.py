import argparse
import os
import glob
import json
from PIL import Image, PngImagePlugin
import sys
import time
from datetime import datetime
try:
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fuzzywuzzy", "python-Levenshtein"])
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process

# For server mode
try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    print("Installing Flask for server mode...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "flask-cors"])
    from flask import Flask, request, jsonify
    from flask_cors import CORS

# Global flag for emoji usage
USE_EMOJIS = True

# Global image database
IMAGE_DATABASE = []

# Function to handle global emoji flag
def set_emoji_mode(disable_emojis=False):
    global USE_EMOJIS
    if disable_emojis:
        USE_EMOJIS = False

# Emoji dictionary for easy switching
EMOJIS = {
    "sparkle": "✨",
    "rocket": "🚀",
    "check": "✅",
    "warning": "⚠️",
    "error": "❌",
    "info": "ℹ️",
    "tag": "🏷️",
    "brain": "🧠",
    "target": "🎯",
    "art": "🎨",
    "save": "💾",
    "database": "🗃️",
    "complete": "🏁",
    "search": "🔍",
    "image": "🖼️",
    "folder": "📁",
    "server": "🌐"
}

# Function to get emoji or empty string based on flag
def get_emoji(key):
    if USE_EMOJIS:
        return EMOJIS.get(key, "")
    return ""

# --- Fancy Logging Helpers ---
def print_header(title):
    """Print a fancy header with emojis."""
    emoji_str = f"{get_emoji('sparkle')}{get_emoji('sparkle')}"
    print(f"\n{'='*60}")
    print(f"{emoji_str}  {title}  {emoji_str}")
    print(f"{'='*60}")

def print_subheader(title, emoji_key="tag"):
    """Print a fancy subheader with emoji."""
    emoji_str = get_emoji(emoji_key)
    print(f"\n{emoji_str} {title} {emoji_str}")

def print_info(message, emoji_key="info"):
    """Print an info message."""
    emoji_str = get_emoji(emoji_key)
    print(f"{emoji_str} {message}")

def print_success(message, emoji_key="check"):
    """Print a success message."""
    emoji_str = get_emoji(emoji_key)
    print(f"{emoji_str} {message}")

def print_warning(message, emoji_key="warning"):
    """Print a warning message."""
    emoji_str = get_emoji(emoji_key)
    print(f"{emoji_str} {message}")

def print_error(message, emoji_key="error"):
    """Print an error message."""
    emoji_str = get_emoji(emoji_key)
    print(f"{emoji_str} {message}")

def print_progress_bar(iteration, total, prefix='', suffix='', length=30, fill='█'):
    """Print a progress bar."""
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
    if iteration == total: 
        print()

def read_metadata_from_image(image_path):
    """
    Read metadata from a PNG image.
    
    Args:
        image_path (str): Path to the PNG image
        
    Returns:
        dict: Dictionary of metadata from the image, or empty dict if no metadata or error
    """
    try:
        with Image.open(image_path) as img:
            if not isinstance(img, Image.Image):
                return {}
                
            # Check if it's a PNG (only PNGs support text chunks)
            if img.format != 'PNG':
                return {}
                
            # Get the metadata from text chunks
            metadata = {}
            for key, value in img.text.items():
                # Try to parse JSON values
                try:
                    metadata[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    metadata[key] = value
                    
            return metadata
    except Exception as e:
        print_error(f"Error reading metadata from {image_path}: {e}")
        return {}

def scan_output_directories():
    """
    Scan all output directories for PNG images and extract their metadata.
    
    Returns:
        list: List of dictionaries containing image info (path, metadata, description)
    """
    global IMAGE_DATABASE
    
    # If we already have a populated database, return it
    if IMAGE_DATABASE:
        return IMAGE_DATABASE
        
    print_subheader("Scanning output directories for images", "folder")
    
    # Get all output directories
    output_dir = "output"
    if not os.path.exists(output_dir):
        print_error(f"Output directory '{output_dir}' not found.")
        return []
        
    # Get absolute path of output directory
    output_dir_abs = os.path.abspath(output_dir)
        
    # Get all subdirectories (config folders)
    config_dirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    
    if not config_dirs:
        print_warning(f"No configuration directories found in '{output_dir}'.")
        return []
        
    print_info(f"Found {len(config_dirs)} configuration directories: {', '.join(config_dirs)}")
    
    # Collect all PNG images
    all_images = []
    total_configs = len(config_dirs)
    
    for i, config_dir in enumerate(config_dirs):
        print_progress_bar(i, total_configs, prefix=f'Scanning {config_dir}:', suffix='Complete', length=40)
        
        config_path = os.path.join(output_dir, config_dir)
        # Use glob to recursively find all PNG files
        png_files = glob.glob(os.path.join(config_path, "**", "*.png"), recursive=True)
        
        print_info(f"Found {len(png_files)} images in '{config_dir}'")
        
        # Process each image
        for j, img_path in enumerate(png_files):
            if j % 10 == 0:  # Update progress every 10 images
                print_progress_bar(j, len(png_files), prefix=f'Processing images:', suffix=f'{j}/{len(png_files)}', length=40)
                
            # Get absolute path
            abs_img_path = os.path.abspath(img_path)
                
            # Read metadata
            metadata = read_metadata_from_image(abs_img_path)
            
            if not metadata:
                continue
                
            # Create a description from prompt and tags
            prompt = metadata.get("Prompt", "")
            tags = metadata.get("Tags", "")
            
            # Combine prompt and tags for searching
            description = f"{prompt} {tags}".lower()
            
            # Store image info
            image_info = {
                "path": abs_img_path,
                "metadata": metadata,
                "description": description,
                "config": config_dir,
                "filename": os.path.basename(abs_img_path)
            }
            
            all_images.append(image_info)
    
    print_progress_bar(total_configs, total_configs, prefix='Scanning:', suffix='Complete', length=40)
    print_success(f"Found a total of {len(all_images)} images with metadata")
    
    # Store in global database
    IMAGE_DATABASE = all_images
    
    return all_images

def search_images(image_list, query, limit=5, threshold=0.5):
    """
    Search for images matching the query using fuzzy matching.
    
    Args:
        image_list (list): List of image info dictionaries
        query (str): Search query
        limit (int): Maximum number of results to return
        threshold (float): Minimum fuzzy match score (0.0 to 1.0)
        
    Returns:
        list: List of matching image info dictionaries, sorted by relevance
    """
    if not image_list:
        return []
        
    print_subheader(f"Searching for: '{query}'", "search")
    
    # Normalize query
    query = query.lower().strip()
    
    # Convert threshold from 0-1 to 0-100 for fuzzywuzzy
    threshold_percent = int(threshold * 100)
    print_info(f"Using fuzzy match threshold: {threshold_percent}%")
    
    # Calculate match scores for each image
    results = []
    
    for img_info in image_list:
        # Get the description to match against
        description = img_info["description"]
        
        # Calculate fuzzy match score
        score = fuzz.partial_ratio(query, description)
        
        # Add to results if score is above threshold
        if score > threshold_percent:
            results.append((score, img_info))
    
    # Sort by score (descending)
    results.sort(reverse=True, key=lambda x: x[0])
    
    # Take top results up to limit
    top_results = results[:limit]
    
    print_success(f"Found {len(top_results)} matches")
    
    # Return just the image info, not the scores
    return [img_info for score, img_info in top_results]

def display_image_info(img_info, index=None):
    """
    Display information about an image in a nice format.
    
    Args:
        img_info (dict): Image info dictionary
        index (int, optional): Result index number
    """
    metadata = img_info["metadata"]
    
    # Format the header
    if index is not None:
        header = f"Result #{index+1}: {os.path.basename(img_info['path'])}"
    else:
        header = f"Image: {os.path.basename(img_info['path'])}"
        
    print(f"\n{get_emoji('image')} {header}")
    print("-" * (len(header) + 4))
    
    # Print path
    print(f"Path: {img_info['path']}")
    
    # Print key metadata
    print(f"Config: {img_info['config']}")
    
    if "Prompt" in metadata:
        print(f"Prompt: {metadata['Prompt']}")
        
    if "Tags" in metadata and metadata["Tags"]:
        print(f"Tags: {metadata['Tags']}")
        
    if "Seed" in metadata:
        print(f"Seed: {metadata['Seed']}")
        
    if "Workflow" in metadata:
        print(f"Workflow: {metadata['Workflow']}")
        
    if "Width" in metadata and "Height" in metadata:
        print(f"Dimensions: {metadata['Width']}x{metadata['Height']}")
        
    if "Created" in metadata:
        print(f"Created: {metadata['Created']}")

def image_info_to_dict(img_info):
    """
    Convert image info to a clean dictionary for JSON serialization.
    
    Args:
        img_info (dict): Image info dictionary
        
    Returns:
        dict: Clean dictionary with selected fields
    """
    metadata = img_info["metadata"]
    
    # Create a clean dictionary with selected fields
    result = {
        "path": img_info["path"],
        "filename": img_info["filename"],
        "config": img_info["config"],
        "metadata": {
            "prompt": metadata.get("Prompt", ""),
            "tags": metadata.get("Tags", ""),
            "seed": metadata.get("Seed", ""),
            "workflow": metadata.get("Workflow", ""),
            "dimensions": f"{metadata.get('Width', '')}x{metadata.get('Height', '')}" if "Width" in metadata and "Height" in metadata else "",
            "created": metadata.get("Created", "")
        }
    }
    
    return result

def start_server(port=5666):
    """
    Start a Flask server for the search API.
    
    Args:
        port (int): Port to listen on
    """
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes
    
    @app.route('/search', methods=['GET'])
    def api_search():
        query = request.args.get('query', '')
        limit = int(request.args.get('limit', 5))
        
        # Get threshold parameter (0.0 to 1.0)
        try:
            threshold = float(request.args.get('threshold', 0.5))
            # Clamp threshold to valid range
            threshold = max(0.0, min(1.0, threshold))
        except ValueError:
            threshold = 0.5
        
        if not query:
            return jsonify({"error": "Query parameter 'query' is required"}), 400
            
        # Make sure we have scanned the images
        image_list = scan_output_directories()
        
        # Perform the search
        results = search_images(image_list, query, limit, threshold)
        
        # Return absolute paths with normalized separators
        paths = [os.path.normpath(img_info["path"]) for img_info in results]
        
        return jsonify(paths)
    
    @app.route('/stats', methods=['GET'])
    def api_stats():
        # Make sure we have scanned the images
        image_list = scan_output_directories()
        
        # Group by config
        configs = {}
        for img_info in image_list:
            config = img_info["config"]
            if config not in configs:
                configs[config] = 0
            configs[config] += 1
            
        return jsonify({
            "total_images": len(image_list),
            "configs": configs
        })
    
    print_header(f"{get_emoji('server')} Starting Search API Server {get_emoji('server')}")
    print_info(f"Server running at http://0.0.0.0:{port}")
    print_info("Available endpoints:")
    print_info("  /search?query=<query>&limit=<limit>&threshold=<0.0-1.0> - Search for images")
    print_info("  /stats - Get image statistics")
    print_info("Press Ctrl+C to stop the server")
    
    # Start the server
    app.run(host="0.0.0.0", port=port, debug=False)

def main():
    parser = argparse.ArgumentParser(
        description="Search for images based on metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for images with "forest" in their description
  python search.py -q "forest"
  
  # Search for images with "portrait" and return up to 10 results
  python search.py -q "portrait" -l 10
  
  # Search for images with multiple terms
  python search.py -q "woman red dress"
  
  # Start the search API server on default port (5666)
  python search.py --server
  
  # Start the search API server on a specific port
  python search.py --server 8080
"""
    )
    
    # Create a mutually exclusive group for search vs server mode
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("-q", "--query", type=str, help="Search query")
    mode_group.add_argument("--server", nargs='?', const=5666, type=int, help="Start in server mode with optional port (default: 5666)")
    
    parser.add_argument("-l", "--limit", type=int, default=5, help="Maximum number of results to return")
    parser.add_argument("-t", "--threshold", type=float, default=0.5, help="Fuzzy matching threshold (0.0 to 1.0)")
    parser.add_argument("--noemoji", action="store_true", help="Disable emojis in output")
    
    args = parser.parse_args()
    
    # Set global emoji flag
    set_emoji_mode(args.noemoji)
    
    # Start timing
    start_time = time.time()
    
    # Pre-accumulate all images at startup
    image_list = scan_output_directories()
    
    if not image_list:
        print_error("No images found with metadata. Generate some images first.")
        sys.exit(1)
    
    # Server mode or search mode
    if args.server is not None:
        start_server(args.server)
    else:
        print_header("🔍 Image Search 🔍")
        
        # Search for images matching the query
        results = search_images(image_list, args.query, args.limit, args.threshold)
        
        # Display results
        if results:
            print_subheader(f"Top {len(results)} Results", "target")
            
            for i, img_info in enumerate(results):
                display_image_info(img_info, i)
        else:
            print_warning(f"No images found matching '{args.query}'")
            
        # Print execution time
        elapsed_time = time.time() - start_time
        print_info(f"\nSearch completed in {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print_warning("Process interrupted by user (Ctrl+C)")
        print_info("Exiting gracefully...")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        sys.exit(1)
