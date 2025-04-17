"""
MongoDB database module for tracking generated images.
Stores image metadata including filename, tags, prompt, and generation parameters.
"""

import os
import pymongo
from datetime import datetime
import logging
import sys
import subprocess
import time
import platform
import yaml
import argparse

# Global flag for emoji usage
USE_EMOJIS = True

# Function to handle global emoji flag
def set_emoji_mode(disable_emojis=False):
    global USE_EMOJIS
    if disable_emojis:
        USE_EMOJIS = False

# Emoji dictionary for easy switching
EMOJIS = {
    "ok": "✅",
    "warning": "⚠️",
    "error": "❌",
    "database": "📊",
    "connection": "🔗",
    "folder": "📁",
    "collection": "🗂️",
    "list": "📋",
    "clean": "🧹",
    "delete": "🗑️",
    "stats": "📈",
    "storage": "💾",
    "image": "📸",
    "search": "🔍",
    "bye": "👋"
}

# Function to get emoji or empty string based on flag
def get_emoji(key):
    if USE_EMOJIS:
        return EMOJIS.get(key, "")
    return ""

# Special logging function to handle emoji display
def log_message(message, emoji_key=None, end="\n"):
    if emoji_key:
        print(f"{get_emoji(emoji_key)} {message}", end=end)
    else:
        print(message, end=end)

class ImageDatabase:
    def __init__(self, config_path="config.yaml", db_name=None, collection_name=None, data_dir=None):
        """Initialize connection to MongoDB."""
        self.client = None
        self.db = None
        self.collection = None
        self.mongo_process = None
        
        # Load configuration from config file if it exists
        config = {}
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                log_message("Loaded database configuration from config file", "ok")
        except Exception as e:
            log_message(f"Could not load config file: {e}", "warning")
        
        # Get MongoDB settings from config or use defaults
        mongodb_config = config.get('mongodb', {})
        self.db_name = db_name or mongodb_config.get('db_name', "stock_images")
        self.collection_name = collection_name or mongodb_config.get('collection', "images")
        self.data_dir = data_dir or mongodb_config.get('data_dir', "./mongodb_data")
        self.connection_string = mongodb_config.get('connection_string', "mongodb://localhost:27017/")
        
        # Try to connect to MongoDB
        try:
            # Connect to MongoDB using the configured connection string
            self.client = pymongo.MongoClient(self.connection_string, serverSelectionTimeoutMS=1000)
            # Test the connection
            self.client.server_info()
            
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            # Create an index on filename for faster lookups
            self.collection.create_index("filename", unique=True)
            # Create text index on tags and prompt for text search
            self.collection.create_index([("tags", pymongo.TEXT), ("prompt", pymongo.TEXT)])
            
            log_message("Connected to MongoDB", "ok")
        except pymongo.errors.ServerSelectionTimeoutError:
            log_message("MongoDB server not running. Attempting to start it...", "warning")
            
            # Try to start MongoDB
            if self._start_mongodb_server(self.data_dir):
                # Try to connect again
                try:
                    # Connect to MongoDB running on localhost
                    self.client = pymongo.MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
                    # Test the connection
                    self.client.server_info()
                    
                    self.db = self.client[self.db_name]
                    self.collection = self.db[self.collection_name]
                    
                    # Create an index on filename for faster lookups
                    self.collection.create_index("filename", unique=True)
                    # Create text index on tags and prompt for text search
                    self.collection.create_index([("tags", pymongo.TEXT), ("prompt", pymongo.TEXT)])
                    
                    log_message("Connected to MongoDB", "ok")
                except Exception as e:
                    log_message(f"Error connecting to MongoDB after starting it: {e}", "error")
                    self._stop_mongodb_server()
                    sys.exit(1)
            else:
                log_message("Failed to start MongoDB server", "error")
                log_message("Please install MongoDB or start it manually", "warning")
                sys.exit(1)
        except Exception as e:
            log_message(f"Error connecting to MongoDB: {e}", "error")
            log_message("Please check MongoDB installation and configuration", "warning")
            sys.exit(1)
    
    def _start_mongodb_server(self, data_dir):
        """Start MongoDB server as a subprocess."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(data_dir, exist_ok=True)
            
            # Start MongoDB based on the operating system
            system = platform.system()
            
            if system == "Windows":
                # Try using the MongoDB service first
                try:
                    log_message("Attempting to start MongoDB service...", "warning")
                    subprocess.run(["net", "start", "MongoDB"], check=True, capture_output=True)
                    time.sleep(2)  # Give it time to start
                    return True
                except subprocess.CalledProcessError:
                    # Service approach failed, try direct executable
                    log_message("MongoDB service not found. Trying direct executable...", "warning")
                    
                # Try to find mongod.exe in common locations
                possible_paths = [
                    r"C:\Dev\MongoDB\Server\8.0\bin\mongod.exe",  # User's specific installation
                    r"C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe",
                    r"C:\Program Files\MongoDB\Server\5.0\bin\mongod.exe",
                    r"C:\Program Files\MongoDB\Server\4.4\bin\mongod.exe",
                    r"C:\mongodb\bin\mongod.exe"
                ]
                
                mongod_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        mongod_path = path
                        break
                
                if not mongod_path:
                    log_message("Could not find MongoDB executable", "error")
                    return False
                
                # Start MongoDB as a background process
                self.mongo_process = subprocess.Popen(
                    [mongod_path, "--dbpath", data_dir],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                log_message(f"Started MongoDB server (PID: {self.mongo_process.pid})", "ok")
                time.sleep(3)  # Give it time to start
                return True
                
            elif system == "Linux" or system == "Darwin":  # Linux or macOS
                # Try to find mongod in PATH
                try:
                    mongod_path = subprocess.check_output(["which", "mongod"]).decode().strip()
                except subprocess.CalledProcessError:
                    # Try common locations
                    possible_paths = [
                        "/usr/bin/mongod",
                        "/usr/local/bin/mongod"
                    ]
                    
                    mongod_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            mongod_path = path
                            break
                    
                    if not mongod_path:
                        log_message("Could not find MongoDB executable", "error")
                        return False
                
                # Start MongoDB as a background process
                self.mongo_process = subprocess.Popen(
                    [mongod_path, "--dbpath", data_dir],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                log_message(f"Started MongoDB server (PID: {self.mongo_process.pid})", "ok")
                time.sleep(2)  # Give it time to start
                return True
            
            else:
                log_message(f"Unsupported operating system: {system}", "error")
                return False
                
        except Exception as e:
            log_message(f"Error starting MongoDB: {e}", "error")
            return False
    
    def _stop_mongodb_server(self):
        """Stop the MongoDB server if we started it."""
        if self.mongo_process:
            try:
                self.mongo_process.terminate()
                self.mongo_process.wait(timeout=5)
                log_message("Stopped MongoDB server", "ok")
            except Exception as e:
                log_message(f"Error stopping MongoDB server: {e}", "error")
                try:
                    self.mongo_process.kill()
                except:
                    pass
    
    def is_connected(self):
        """Check if database connection is active."""
        return self.client is not None
    
    def add_image(self, filename, tags, prompt, seed=None, steps=None, width=None, height=None, workflow=None, ratio=None):
        """Add a new image entry to the database."""
        if not self.is_connected():
            log_message("Database not connected, cannot register image", "warning")
            return False
            
        try:
            # Create image document
            image_doc = {
                "filename": filename,
                "tags": tags,
                "prompt": prompt,
                "seed": seed,
                "steps": steps,
                "width": width,
                "height": height,
                "workflow": workflow,
                "ratio": ratio,
                "created_at": datetime.now()
            }
            
            # Insert or update if exists
            result = self.collection.update_one(
                {"filename": filename},
                {"$set": image_doc},
                upsert=True
            )
            
            return result.acknowledged
        except Exception as e:
            log_message(f"Error adding image to database: {e}", "error")
            return False
    
    def get_image(self, filename):
        """Get image details by filename."""
        if not self.is_connected():
            return None
            
        try:
            return self.collection.find_one({"filename": filename})
        except Exception as e:
            log_message(f"Error retrieving image from database: {e}", "error")
            return None
    
    def search_by_tags(self, tags, match_all=False, limit=100):
        """
        Search for images based on tags.
        
        Args:
            tags (list): List of tags to search for. Can be in format ["subject:person", "mood:happy"] 
                         or just ["person", "happy"]
            match_all (bool): If True, all tags must match. If False, any tag can match.
            limit (int): Maximum number of results to return
            
        Returns:
            list: List of matching image documents
        """
        if not self.is_connected() or not tags:
            return []
            
        try:
            # Process the tags to handle both formats (with or without categories)
            processed_tags = []
            for tag in tags:
                tag = tag.strip()
                if ":" in tag:
                    # Format is "category:value"
                    category, value = tag.split(":", 1)
                    # Create a query to match this specific category:value pair
                    processed_tags.append({f"tags.{category}": value})
                else:
                    # Format is just "value" - search in all tag values
                    # This creates a query that checks if the tag appears as any value in the tags object
                    processed_tags.append({"$or": [
                        {f"tags.{field}": {"$regex": tag, "$options": "i"}} 
                        for field in ["subject", "action", "setting", "mood", "style", "lighting", "camera_angle"]
                    ]})
            
            # Build query based on match_all parameter
            if match_all:
                # All conditions must be met
                query = {"$and": processed_tags}
            else:
                # Any condition can match
                query = {"$or": processed_tags}
            
            # Execute query
            cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            log_message(f"Error searching images by tags: {e}", "error")
            return []
    
    def text_search(self, search_text, limit=100):
        """
        Perform a text search on tags and prompt fields.
        
        Args:
            search_text (str): Text to search for
            limit (int): Maximum number of results to return
            
        Returns:
            list: List of matching image documents
        """
        if not self.is_connected() or not search_text:
            return []
            
        try:
            # Use MongoDB text search
            query = {"$text": {"$search": search_text}}
            # Sort by text score (relevance)
            cursor = self.collection.find(
                query,
                {"score": {"$meta": "textScore"}}
            ).sort(
                [("score", {"$meta": "textScore"})]
            ).limit(limit)
            
            return list(cursor)
        except Exception as e:
            log_message(f"Error performing text search: {e}", "error")
            return []
    
    def get_all_images(self, limit=100):
        """Get all images, newest first."""
        if not self.is_connected():
            return []
            
        try:
            cursor = self.collection.find().sort("created_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            log_message(f"Error retrieving all images from database: {e}", "error")
            return []
    
    def get_unique_tags(self):
        """Get a list of all unique tags used across all images."""
        if not self.is_connected():
            return []
            
        try:
            # Use MongoDB's aggregation pipeline to extract unique tags
            pipeline = [
                {"$project": {"tags": 1}},
                {"$unwind": "$tags"},
                {"$group": {"_id": "$tags"}},
                {"$sort": {"_id": 1}}
            ]
            
            result = self.collection.aggregate(pipeline)
            return [doc["_id"] for doc in result]
        except Exception as e:
            log_message(f"Error retrieving unique tags: {e}", "error")
            return []
    
    def delete_image(self, filename):
        """Delete an image entry from the database."""
        if not self.is_connected():
            return False
            
        try:
            result = self.collection.delete_one({"filename": filename})
            return result.deleted_count > 0
        except Exception as e:
            log_message(f"Error deleting image from database: {e}", "error")
            return False
    
    def search_by_workflow(self, workflow, limit=100):
        """
        Search for images generated with a specific workflow.
        
        Args:
            workflow (str): Workflow name to search for
            limit (int): Maximum number of results to return
            
        Returns:
            list: List of matching image documents
        """
        if not self.is_connected() or not workflow:
            return []
            
        try:
            # Find images with the specified workflow
            query = {"workflow": workflow}
            cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            log_message(f"Error searching images by workflow: {e}", "error")
            return []
    
    def search_by_ratio(self, ratio, tolerance=0.1, limit=100):
        """
        Search for images with a specific aspect ratio (within tolerance).
        
        Args:
            ratio (float): Aspect ratio to search for (width/height)
            tolerance (float): Tolerance for ratio matching
            limit (int): Maximum number of results to return
            
        Returns:
            list: List of matching image documents
        """
        if not self.is_connected() or not ratio:
            return []
            
        try:
            # Find images with ratio within the specified tolerance
            min_ratio = ratio - tolerance
            max_ratio = ratio + tolerance
            query = {"ratio": {"$gte": min_ratio, "$lte": max_ratio}}
            cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            log_message(f"Error searching images by ratio: {e}", "error")
            return []
    
    def close(self):
        """Close the database connection and stop MongoDB if we started it."""
        if self.client:
            self.client.close()
        
        # Stop MongoDB if we started it
        self._stop_mongodb_server()

# CLI mode for database management
if __name__ == "__main__":
    import argparse
    
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="MongoDB Database Management for Stock Images Generator")
    parser.add_argument("--info", action="store_true", help="Display database connection information")
    parser.add_argument("--list", action="store_true", help="List all images in the database")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--trim", action="store_true", help="Remove database records for which image files don't exist")
    parser.add_argument("--output-dir", type=str, default="output_images", help="Directory to check for image files when using --trim")
    parser.add_argument("--noemoji", action="store_true", help="Disable emojis in output")
    args = parser.parse_args()
    
    # Set global emoji flag
    if args.noemoji:
        set_emoji_mode(disable_emojis=True)
    
    # Initialize database connection
    log_message("Initializing database connection...")
    db = ImageDatabase()
    
    if not db.is_connected():
        log_message("Failed to connect to database", "error")
        sys.exit(1)
    
    # Print connection information (useful for MongoDB Atlas)
    log_message("\nDatabase Connection Information:")
    log_message("--------------------------------")
    log_message(f"Connection: {db.connection_string}")
    log_message(f"Database: {db.db_name}")
    log_message(f"Collection: {db.collection_name}")
    log_message("--------------------------------")
    
    # Handle specific commands
    if args.list:
        log_message("\nImages in Database:")
        images = db.get_all_images(limit=10)
        if images:
            for i, img in enumerate(images, 1):
                log_message(f"{i}. {img['filename']} - Created: {img['created_at']}")
                log_message(f"   Tags: {img.get('tags', 'None')}")
                log_message(f"   Prompt: {img.get('prompt', 'None')[:50]}...")
        else:
            log_message("No images found in database.")
    
    if args.trim:
        log_message("\nTrimming Database Records:")
        output_dir = args.output_dir
        if not os.path.exists(output_dir):
            log_message(f"Output directory '{output_dir}' does not exist.", "error")
        else:
            # Get all images from database
            all_images = db.get_all_images(limit=1000)  # Set a reasonable limit
            removed_count = 0
            
            for img in all_images:
                filename = img.get('filename')
                if not filename:
                    continue
                
                # Check if the image file exists
                filepath = os.path.join(output_dir, filename)
                if not os.path.exists(filepath):
                    # Image file doesn't exist, remove from database
                    # Get a shortened filename for display
                    short_filename = filename
                    if len(short_filename) > 50:
                        short_filename = short_filename[:25] + "..." + short_filename[-22:]
                    log_message(f"Removing: {short_filename}", "delete")
                    db.delete_image(filename)
                    removed_count += 1
            
            if removed_count > 0:
                log_message(f"Cleaned up {removed_count} records for missing files", "clean")
            else:
                log_message("No missing files found. Database is clean")
    
    if args.stats:
        log_message("\nDatabase Statistics:")
        try:
            count = db.collection.count_documents({})
            log_message(f"Total Images: {count}")
            
            # Get unique tags count
            unique_tags = db.get_unique_tags()
            log_message(f"Unique Tags: {len(unique_tags)}")
            
            # Get storage size
            stats = db.db.command("dbStats")
            storage_mb = stats.get("storageSize", 0) / (1024 * 1024)
            log_message(f"Storage Size: {storage_mb:.2f} MB", "storage")
            
            # Get most recent image
            latest = db.collection.find_one({}, sort=[("created_at", -1)])
            if latest:
                log_message(f"Most Recent Image: {latest['filename']}", "image")
                log_message(f"Created: {latest['created_at']}")
        except Exception as e:
            log_message(f"Error getting statistics: {e}", "error")
    
    # If no specific command, just show info
    if not (args.list or args.stats or args.trim) or args.info:
        log_message("\nDatabase Status:")
        try:
            count = db.collection.count_documents({})
            log_message(f"Total Images: {count}")
            log_message("Database is ready", "ok")
        except Exception as e:
            log_message(f"{e}", "error")
    
    # Close the connection
    log_message("\nClosing database connection...")
    db.close()
    log_message("Done!", "bye")
