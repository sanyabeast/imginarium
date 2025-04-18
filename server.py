#!/usr/bin/env python
"""
Image Search Server - HTTP API for searching generated images

This script provides a Flask-based HTTP server that allows searching
for generated images across different configurations and workflows.
"""

import os
import sys
import json
import argparse
import random
from flask import Flask, request, jsonify
from db import ImageDatabase
import yaml
from difflib import SequenceMatcher
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Global variables
CONFIG_DIR = "configs"
OUTPUT_DIR = "output"

def load_all_configs():
    """Load all configuration files from the configs directory."""
    configs = {}
    for filename in os.listdir(CONFIG_DIR):
        if filename.endswith(".yaml"):
            config_name = os.path.splitext(filename)[0]
            config_path = os.path.join(CONFIG_DIR, filename)
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    configs[config_name] = yaml.safe_load(f)
                    logger.info(f"Loaded config: {config_name}")
            except Exception as e:
                logger.error(f"Error loading config {config_name}: {e}")
    return configs

def fuzzy_match(query, target, threshold=0.6):
    """
    Check if query fuzzy matches target with a similarity score above threshold.
    
    Args:
        query: The search term
        target: The string to match against
        threshold: Minimum similarity score (0-1) to consider a match
        
    Returns:
        bool: True if it's a match, False otherwise
    """
    # Handle None values
    if query is None or target is None:
        return False
    
    # Convert to strings if they aren't already
    query = str(query).lower()
    target = str(target).lower()
    
    # Direct substring match
    if query in target:
        return True
    
    # Fuzzy match using sequence matcher
    similarity = SequenceMatcher(None, query, target).ratio()
    return similarity >= threshold

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

def search_images(configs, workflows=None, tags=None, limit=1, verbose=True):
    """
    Search for images across specified configurations and workflows.
    
    Args:
        configs: List of configuration names to search in
        workflows: List of workflow names to filter by
        tags: List of tags to search for
        limit: Maximum number of images to return
        verbose: Whether to return full image details or just paths
        
    Returns:
        list: List of image information dictionaries or paths
    """
    results = []
    
    # Load all configurations if none specified
    if not configs:
        config_files = [f for f in os.listdir(CONFIG_DIR) if f.endswith(".yaml")]
        configs = [os.path.splitext(f)[0] for f in config_files]
    
    # Process each configuration
    for config_name in configs:
        config_path = os.path.join(CONFIG_DIR, f"{config_name}.yaml")
        
        # Skip if config file doesn't exist
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found: {config_path}")
            continue
        
        # Load configuration
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config {config_name}: {e}")
            continue
        
        # Connect to the database for this configuration
        try:
            db = ImageDatabase(config_path=config_path)
            
            # Build query
            query = {}
            
            # Filter by workflow if specified
            if workflows:
                workflow_query = []
                for workflow in workflows:
                    workflow_name = os.path.splitext(workflow)[0] if '.' in workflow else workflow
                    workflow_query.append({"workflow": {"$regex": f".*{workflow_name}.*", "$options": "i"}})
                
                if workflow_query:
                    query["$or"] = workflow_query
            
            # Find images matching the query
            images = list(db.collection.find(query))
            
            # Filter by tags if specified
            if tags and len(tags) > 0:
                filtered_images = []
                
                # Get tag categories from config
                tag_categories = config.get('tags', {})
                
                # Process each image
                for image in images:
                    image_tags = image.get('tags', {})
                    
                    # Check if any of the search tags match this image's tags
                    matches = False
                    for search_tag in tags:
                        # Find potential matching tags in the config
                        matching_config_tags = []
                        for category, category_tags in tag_categories.items():
                            for tag in category_tags:
                                if fuzzy_match(search_tag, tag):
                                    matching_config_tags.append((category, tag))
                        
                        # Check if any of the image's tags match the potential matches
                        for category, tag in matching_config_tags:
                            if category in image_tags and fuzzy_match(tag, image_tags[category]):
                                matches = True
                                break
                        
                        # Also check direct match in image tags
                        for category, value in image_tags.items():
                            if fuzzy_match(search_tag, value):
                                matches = True
                                break
                        
                        if matches:
                            break
                    
                    if matches:
                        filtered_images.append(image)
                
                images = filtered_images
            
            # Add configuration name to each image and check if file exists
            for image in images:
                # Add configuration name
                image['config'] = config_name
                
                # Add absolute path to the image
                image_path = os.path.join(OUTPUT_DIR, config_name, image['filename'])
                absolute_path = os.path.abspath(image_path)
                
                # Check if the image file exists on disk
                if os.path.exists(absolute_path) and os.path.isfile(absolute_path):
                    if verbose:
                        # Convert ObjectId to string for JSON serialization
                        if '_id' in image:
                            image['_id'] = str(image['_id'])
                        
                        # Convert datetime to string for JSON serialization
                        if 'created_at' in image:
                            image['created_at'] = image['created_at'].isoformat()
                        
                        image['absolute_path'] = absolute_path
                        image['exists'] = True
                        results.append(image)
                    else:
                        # Just add the path if verbose is False
                        results.append(absolute_path)
                else:
                    if verbose:
                        logger.warning(f"Image file not found on disk: {absolute_path}")
            
        except Exception as e:
            logger.error(f"Error searching in config {config_name}: {e}")
            continue
    
    # If verbose mode, sort by creation date (newest first)
    # Otherwise, results are just paths and we don't need to sort them
    if verbose:
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Randomize results if there are more matches than the requested limit
    if len(results) > limit:
        random.shuffle(results)
    
    # Limit the number of results
    if limit > 0:
        results = results[:limit]
    
    return results

@app.route('/search', methods=['POST'])
def search_endpoint_json():
    """
    Endpoint for searching images using JSON parameters.
    
    JSON parameters:
    - configs: List of configuration names (optional, defaults to all configs)
    - workflows: List of workflow names (optional, defaults to all workflows)
    - tags: List of tags (optional)
    - limit: Maximum number of images to return (default: 1)
    - verbose: Whether to return full image details or just paths (default: true)
    
    Returns:
        JSON: List of image information dictionaries or paths
    """
    # Get JSON data from request
    data = request.get_json(silent=True) or {}
    
    # Parse parameters
    configs = data.get('configs', [])
    workflows = data.get('workflows', [])
    tags = data.get('tags', [])
    limit = data.get('limit', 1)
    verbose = data.get('verbose', True)
    
    # Ensure limit is an integer
    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 1
    
    # Ensure verbose is a boolean
    verbose = bool(verbose)
    
    # Log the request
    logger.info(f"Search request (JSON) - configs: {configs}, workflows: {workflows}, tags: {tags}, limit: {limit}, verbose: {verbose}")
    
    # Perform the search
    results = search_images(configs, workflows, tags, limit, verbose)
    
    # Return the results
    return jsonify(results)

@app.route('/search', methods=['GET'])
def search_endpoint_query():
    """
    Endpoint for searching images using query parameters.
    
    Query parameters:
    - configs: Comma-separated list of configuration names
    - workflows: Comma-separated list of workflow names
    - tags: Comma-separated list of tags
    - limit: Maximum number of images to return (default: 1)
    - verbose: Whether to return full image details or just paths (default: true)
    
    Returns:
        JSON: List of image information dictionaries or paths
    """
    # Parse query parameters
    configs_param = request.args.get('configs', '')
    workflows_param = request.args.get('workflows', '')
    tags_param = request.args.get('tags', '')
    limit_param = request.args.get('limit', '1')
    verbose_param = request.args.get('verbose', 'true')
    
    # Process parameters
    configs = [c.strip() for c in configs_param.split(',')] if configs_param else []
    workflows = [w.strip() for w in workflows_param.split(',')] if workflows_param else []
    tags = [t.strip() for t in tags_param.split(',')] if tags_param else []
    
    try:
        limit = int(limit_param)
    except ValueError:
        limit = 1
    
    # Convert verbose string to boolean
    verbose = verbose_param.lower() in ('true', 'yes', '1', 't', 'y')
    
    # Log the request
    logger.info(f"Search request (Query) - configs: {configs}, workflows: {workflows}, tags: {tags}, limit: {limit}, verbose: {verbose}")
    
    # Perform the search
    results = search_images(configs, workflows, tags, limit, verbose)
    
    # Return the results
    return jsonify(results)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Image Search Server")
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5666, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Log startup information
    logger.info(f"Starting Image Search Server on {args.host}:{args.port}")
    logger.info(f"Debug mode: {args.debug}")
    
    # Start the server
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
