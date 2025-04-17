#!/usr/bin/env python
"""
Image Finder - Search for generated stock images by tags

This script allows you to search for images in your MongoDB registry
by specifying tags, performing text searches, or browsing all images.
"""

import os
import argparse
import sys
from db import ImageDatabase
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import yaml
from PIL import Image
import re
from difflib import SequenceMatcher

# Import the metadata reading function from generate.py
from generate import read_metadata_from_image, print_header, print_info, print_error, print_warning, print_success, print_subheader

console = Console()

# Function to handle global emoji flag
def set_emoji_mode(disable_emojis=False):
    global USE_EMOJIS
    if disable_emojis:
        USE_EMOJIS = False

# Global flag for emoji usage
USE_EMOJIS = True

# Emoji dictionary for easy switching
EMOJIS = {
    "search": "🔍",
    "list": "📋",
    "info": "ℹ️",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "image": "🖼️",
    "tag": "🏷️",
    "date": "📅",
    "prompt": "💬"
}

# Function to get emoji or empty string based on flag
def get_emoji(key):
    if USE_EMOJIS:
        return EMOJIS.get(key, "")
    return ""

def load_config():
    """Load configuration from config.yaml."""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        console.print(f"[bold red]Error loading config:[/bold red] {e}")
        return {}

def load_tag_categories():
    """Load tag categories from config.yaml."""
    config = load_config()
    return config.get('tags', {})

def find_matching_tags(search_term, tag_categories, threshold=0.6):
    """
    Find matching tags from the configured tag categories.
    
    Args:
        search_term: The user's search term
        tag_categories: Dictionary of tag categories from config.yaml
        threshold: Minimum similarity score for fuzzy matching
        
    Returns:
        list: List of tuples (category, tag) that match the search term
    """
    matches = []
    
    # Convert search term to lowercase for case-insensitive matching
    search_term = search_term.lower()
    
    # Check each category and its tags
    for category, tags in tag_categories.items():
        for tag in tags:
            # Check for direct substring match
            if search_term in tag.lower():
                matches.append((category, tag))
                continue
                
            # Check for fuzzy match
            similarity = SequenceMatcher(None, search_term, tag.lower()).ratio()
            if similarity >= threshold:
                matches.append((category, tag))
    
    return matches

def print_header(text):
    """Print a fancy header."""
    emoji_str = get_emoji("search")
    console.print(f"\n[bold cyan]{emoji_str} {text} {emoji_str}[/bold cyan]")

def print_subheader(text):
    """Print a fancy subheader."""
    emoji_str = get_emoji("list")
    console.print(f"[bold blue]{emoji_str} {text}[/bold blue]")

def print_info(text):
    """Print an info message."""
    emoji_str = get_emoji("info")
    console.print(f"[blue]{emoji_str} {text}[/blue]")

def print_success(text):
    """Print a success message."""
    emoji_str = get_emoji("success")
    console.print(f"[bold green]{emoji_str} {text}[/bold green]")

def print_error(text):
    """Print an error message."""
    emoji_str = get_emoji("error")
    console.print(f"[bold red]{emoji_str} {text}[/bold red]")

def print_warning(text):
    """Print a warning message."""
    emoji_str = get_emoji("warning")
    console.print(f"[bold yellow]{emoji_str} {text}[/bold yellow]")

def print_image_details(image, index=None):
    """Print details of an image in a rich panel."""
    # Format the header with index if provided
    header = f"[bold magenta]{image['filename']}[/bold magenta]"
    if index is not None:
        header = f"[bold white]{index}.[/bold white] {header}"
    
    # Create a list to hold the content lines
    content = []
    
    # Add tags with category highlighting if available
    tags_str = image.get('tags', '')
    formatted_tags = []
    
    # Handle tags based on type (string or dict)
    if isinstance(tags_str, str):
        # Handle string format (comma-separated)
        for tag in tags_str.split(', '):
            if ':' in tag:
                # Tag already has category in format "category:value"
                category, value = tag.split(':', 1)
                formatted_tags.append(f"[bold yellow]{category}:[/bold yellow][green]{value}[/green]")
            else:
                formatted_tags.append(f"[green]{tag}[/green]")
    elif isinstance(tags_str, dict):
        # Handle dictionary format
        for category, values in tags_str.items():
            if isinstance(values, list):
                for value in values:
                    formatted_tags.append(f"[bold yellow]{category}:[/bold yellow][green]{value}[/green]")
            else:
                formatted_tags.append(f"[bold yellow]{category}:[/bold yellow][green]{values}[/green]")
    
    content.append(f"[bold]Tags:[/bold] {', '.join(formatted_tags)}")
    
    # Add prompt with truncation if too long
    prompt = image.get('prompt', '')
    if len(prompt) > 100:
        prompt = prompt[:97] + "..."
    content.append(f"[bold]Prompt:[/bold] {prompt}")
    
    # Add generation parameters if available
    params = []
    if image.get('seed'):
        params.append(f"seed={image['seed']}")
    if image.get('steps'):
        params.append(f"steps={image['steps']}")
    if image.get('width') and image.get('height'):
        params.append(f"size={image['width']}x{image['height']}")
    if image.get('ratio'):
        params.append(f"ratio={image['ratio']:.2f}")
    if image.get('workflow'):
        params.append(f"workflow={image['workflow']}")
    
    if params:
        content.append(f"[bold]Parameters:[/bold] {', '.join(params)}")
    
    # Add creation date if available
    if image.get('created_at'):
        content.append(f"[bold]Created:[/bold] {image['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Add file path
    file_path = os.path.join("output_images", image['filename'])
    content.append(f"[bold]Path:[/bold] [italic]{file_path}[/italic]")
    
    # Create and print the panel
    panel = Panel(
        "\n".join(content),
        title=header,
        border_style="blue",
        box=box.ROUNDED
    )
    console.print(panel)

def fuzzy_match(query, target, threshold=0.5):
    """
    Check if query fuzzy matches target with a similarity score above threshold.
    
    Args:
        query: The search term
        target: The string to match against
        threshold: Minimum similarity score (0-1) to consider a match
        
    Returns:
        bool: True if it's a match, False otherwise
    """
    # Convert target to string if it's not already
    if not isinstance(target, str):
        if isinstance(target, dict):
            # For dictionaries, check each value
            for key, value in target.items():
                if isinstance(value, list):
                    for item in value:
                        if fuzzy_match(query, str(item), threshold):
                            return True
                else:
                    if fuzzy_match(query, str(value), threshold):
                        return True
            return False
        else:
            # Convert other types to string
            target = str(target)
    
    # Direct match
    if query.lower() in target.lower():
        return True
        
    # Fuzzy match using sequence matcher
    similarity = SequenceMatcher(None, query.lower(), target.lower()).ratio()
    return similarity >= threshold

def list_available_tags(db):
    """List all available tags in the database."""
    print_header("Available Tags")
    
    # Get all unique tags from the database
    tags = db.get_unique_tags()
    
    if not tags:
        print_warning("No tags found in the database.")
        return
    
    # Load config to get tag categories
    config = load_config()
    tag_categories = {}
    
    if config and 'tags' in config:
        # Create a mapping of tag values to their categories
        for category, values in config['tags'].items():
            for value in values:
                tag_categories[value] = category
    
    # Group tags by category
    categorized_tags = {}
    uncategorized = []
    
    for tag in tags:
        # Check if the tag is in our config categories
        if ':' in tag:
            # Tag already has category in format "category:value"
            category, value = tag.split(':', 1)
            if category not in categorized_tags:
                categorized_tags[category] = []
            categorized_tags[category].append(value)
        elif tag in tag_categories:
            # Tag is in our config
            category = tag_categories[tag]
            if category not in categorized_tags:
                categorized_tags[category] = []
            categorized_tags[category].append(tag)
        else:
            # Tag is not in any category
            uncategorized.append(tag)
    
    # Print tags by category
    for category, values in sorted(categorized_tags.items()):
        print_subheader(f"{category.title()}")
        # Create a table for this category
        table = Table(show_header=False, box=box.SIMPLE)
        
        # Add tags in rows of 4
        row = []
        for value in sorted(values):
            row.append(value)
            if len(row) == 4:
                table.add_row(*row)
                row = []
        
        # Add any remaining tags
        if row:
            # Pad the row with empty strings
            while len(row) < 4:
                row.append("")
            table.add_row(*row)
        
        console.print(table)
        console.print("")
    
    # Print uncategorized tags if any
    if uncategorized:
        print_subheader("Uncategorized")
        table = Table(show_header=False, box=box.SIMPLE)
        
        # Add tags in rows of 4
        row = []
        for tag in sorted(uncategorized):
            row.append(tag)
            if len(row) == 4:
                table.add_row(*row)
                row = []
        
        # Add any remaining tags
        if row:
            # Pad the row with empty strings
            while len(row) < 4:
                row.append("")
            table.add_row(*row)
        
        console.print(table)

def search_by_tags(db, tags_input, match_all=False):
    """Search for images by tags."""
    if not tags_input:
        print_warning("No tags specified for search.")
        return
    
    # Split the input tags by comma
    search_terms = [term.strip() for term in tags_input.split(',')]
    
    print_header(f"Searching for images with tags: {tags_input}")
    if match_all:
        print_info("Matching ALL specified tags")
    else:
        print_info("Matching ANY specified tag")
    
    # Load tag categories from config
    tag_categories = load_tag_categories()
    
    # Find matching tags for each search term
    all_matched_tags = []
    for term in search_terms:
        matches = find_matching_tags(term, tag_categories)
        
        if matches:
            formatted_matches = [f"{category}:{tag}" for category, tag in matches]
            print_info(f"'{term}' matched to: {', '.join(formatted_matches)}")
            all_matched_tags.extend(formatted_matches)
        else:
            print_warning(f"No matches found for tag: '{term}'")
    
    if not all_matched_tags:
        print_warning("No matching tags found in the configuration.")
        return
    
    # Search the database with the matched tags
    results = db.search_by_tags(all_matched_tags, match_all)
    
    if not results:
        print_warning("No images found matching these tags.")
        return
    
    print_success(f"Found {len(results)} matching images:")
    
    # Print each image's details
    for i, image in enumerate(results, 1):
        print_image_details(image, i)

def text_search(db, query):
    """Perform a text search on tags and prompts."""
    print_header(f"Text search: '{query}'")
    
    # Search the database
    results = db.text_search(query)
    
    if not results:
        print_warning("No images found matching this search query.")
        return
    
    print_success(f"Found {len(results)} matching images:")
    
    # Print each image's details
    for i, image in enumerate(results, 1):
        print_image_details(image, i)

def list_recent_images(db, limit=10):
    """List the most recent images."""
    print_header(f"Most recent {limit} images")
    
    # Get images from the database
    results = db.get_all_images(limit)
    
    if not results:
        print_warning("No images found in the database.")
        return
    
    print_success(f"Found {len(results)} images:")
    
    # Print each image's details
    for i, image in enumerate(results, 1):
        print_image_details(image, i)

def search_by_workflow(db, workflow):
    """Search for images by workflow."""
    print_header(f"Images Generated with Workflow: {workflow}")
    
    # Search for images with the specified workflow
    results = db.search_by_workflow(workflow)
    
    if not results:
        print_warning(f"No images found with workflow '{workflow}'.")
        return
    
    print_success(f"Found {len(results)} images.")
    
    # Print each image's details
    for i, image in enumerate(results, 1):
        print_image_details(image, i)

def search_by_ratio(db, ratio, tolerance=0.1):
    """Search for images by aspect ratio."""
    print_header(f"Images with Aspect Ratio: {ratio} (±{tolerance})")
    
    # Convert ratio to float if it's a string
    if isinstance(ratio, str):
        try:
            if ':' in ratio:
                # Handle ratios like "16:9"
                w, h = map(float, ratio.split(':'))
                ratio = w / h
            else:
                ratio = float(ratio)
        except ValueError:
            print_error(f"Invalid ratio format: {ratio}")
            return
    
    # Search for images with the specified ratio
    results = db.search_by_ratio(ratio, tolerance)
    
    if not results:
        print_warning(f"No images found with ratio {ratio} (±{tolerance}).")
        return
    
    print_success(f"Found {len(results)} images.")
    
    # Print each image's details
    for i, image in enumerate(results, 1):
        print_image_details(image, i)

def show_image_metadata(image_path):
    """Display metadata embedded in a PNG image."""
    print_header(f"Image Metadata")
    
    # Get the metadata
    metadata = read_metadata_from_image(image_path)
    
    if not metadata:
        print_warning(f"No metadata found in image: {image_path}")
        return
    
    print_success(f"Found {len(metadata)} metadata entries in: {os.path.basename(image_path)}")
    
    # Create a panel to display the metadata
    content = []
    
    # Add each metadata item
    for key, value in metadata.items():
        content.append(f"[bold]{key}:[/bold] {value}")
    
    # Create and print the panel
    panel = Panel(
        "\n".join(content),
        title=f"[bold magenta]{os.path.basename(image_path)}[/bold magenta]",
        border_style="blue",
        box=box.ROUNDED
    )
    console.print(panel)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Search for generated stock images by tags",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available tags
  python image_finder.py --list-tags
  
  # List 5 most recent images
  python image_finder.py --recent 5
  
  # Search for images with ANY of these tags
  python image_finder.py --tags robot,dancing,steampunk
  
  # Search for images with ALL of these tags
  python image_finder.py --tags robot,dancing,steampunk --match-all
  
  # Perform a text search (searches in tags and prompts)
  python image_finder.py --search "abandoned factory"
  
  # Search for images generated with a specific workflow
  python image_finder.py --workflow "stable-diffusion"
  
  # Search for images with a specific aspect ratio
  python image_finder.py --ratio "16:9"
  
  # Display metadata from a PNG image
  python image_finder.py --metadata image.png
        """
    )
    
    # Create mutually exclusive group for the main actions
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--list-tags", action="store_true", help="List all available tags")
    action_group.add_argument("--tags", type=str, help="Search for images with these tags (comma-separated)")
    action_group.add_argument("--search", type=str, help="Text search in tags and prompts")
    action_group.add_argument("--recent", type=int, nargs="?", const=10, help="List recent images (default: 10)")
    action_group.add_argument("--workflow", type=str, help="Search for images generated with this workflow")
    action_group.add_argument("--ratio", type=str, help="Search for images with this aspect ratio")
    action_group.add_argument("--metadata", type=str, help="Display metadata from a PNG image")
    
    # Additional options
    parser.add_argument("--match-all", action="store_true", help="When using --tags, require ALL tags to match (default: match ANY)")
    parser.add_argument("--tolerance", type=float, default=0.1, help="Tolerance for aspect ratio search (default: 0.1)")
    parser.add_argument("--noemoji", action="store_true", help="Disable emojis in output")
    
    args = parser.parse_args()
    
    # Set global emoji flag
    if args.noemoji:
        set_emoji_mode(disable_emojis=True)
    
    # Connect to the database
    db = ImageDatabase()
    
    if not db.is_connected():
        print_error("Could not connect to the MongoDB database.")
        print_warning("Make sure MongoDB is running and try again.")
        sys.exit(1)
    
    try:
        # Execute the requested action
        if args.list_tags:
            list_available_tags(db)
        elif args.tags:
            search_by_tags(db, args.tags, args.match_all)
        elif args.search:
            text_search(db, args.search)
        elif args.recent is not None:
            list_recent_images(db, args.recent)
        elif args.workflow:
            search_by_workflow(db, args.workflow)
        elif args.ratio:
            search_by_ratio(db, args.ratio, args.tolerance)
        elif args.metadata:
            show_image_metadata(args.metadata)
    except KeyboardInterrupt:
        print("\n")
        print_info("Search cancelled by user.")
    finally:
        # Close the database connection
        db.close()

if __name__ == "__main__":
    main()
