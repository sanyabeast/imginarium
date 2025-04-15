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

class ImageDatabase:
    def __init__(self, db_name="stock_images", collection_name="images", data_dir="./mongodb_data"):
        """Initialize connection to MongoDB."""
        self.client = None
        self.db = None
        self.collection = None
        self.mongo_process = None
        
        # Try to connect to MongoDB
        try:
            # Connect to MongoDB running on localhost with a short timeout
            self.client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=1000)
            # Test the connection
            self.client.server_info()
            
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            
            # Create an index on filename for faster lookups
            self.collection.create_index("filename", unique=True)
            # Create text index on tags and prompt for text search
            self.collection.create_index([("tags", pymongo.TEXT), ("prompt", pymongo.TEXT)])
            
            print("✅ Connected to MongoDB database")
        except pymongo.errors.ServerSelectionTimeoutError:
            print("⚠️ MongoDB server not running. Attempting to start it...")
            
            # Try to start MongoDB
            if self._start_mongodb_server(data_dir):
                # Try to connect again
                try:
                    # Connect to MongoDB running on localhost
                    self.client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
                    # Test the connection
                    self.client.server_info()
                    
                    self.db = self.client[db_name]
                    self.collection = self.db[collection_name]
                    
                    # Create an index on filename for faster lookups
                    self.collection.create_index("filename", unique=True)
                    # Create text index on tags and prompt for text search
                    self.collection.create_index([("tags", pymongo.TEXT), ("prompt", pymongo.TEXT)])
                    
                    print("✅ Connected to MongoDB database")
                except Exception as e:
                    print(f"❌ Error connecting to MongoDB after starting it: {e}")
                    self._stop_mongodb_server()
                    sys.exit(1)
            else:
                print("❌ Failed to start MongoDB server")
                print("⚠️ Please install MongoDB or start it manually")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error connecting to MongoDB: {e}")
            print("⚠️ Please check MongoDB installation and configuration")
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
                    print("Attempting to start MongoDB service...")
                    subprocess.run(["net", "start", "MongoDB"], check=True, capture_output=True)
                    time.sleep(2)  # Give it time to start
                    return True
                except subprocess.CalledProcessError:
                    # Service approach failed, try direct executable
                    print("MongoDB service not found. Trying direct executable...")
                    
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
                    print("❌ Could not find MongoDB executable")
                    return False
                
                # Start MongoDB as a background process
                self.mongo_process = subprocess.Popen(
                    [mongod_path, "--dbpath", data_dir],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                print(f"Started MongoDB server (PID: {self.mongo_process.pid})")
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
                        print("❌ Could not find MongoDB executable")
                        return False
                
                # Start MongoDB as a background process
                self.mongo_process = subprocess.Popen(
                    [mongod_path, "--dbpath", data_dir],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                print(f"Started MongoDB server (PID: {self.mongo_process.pid})")
                time.sleep(2)  # Give it time to start
                return True
            
            else:
                print(f"❌ Unsupported operating system: {system}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting MongoDB: {e}")
            return False
    
    def _stop_mongodb_server(self):
        """Stop the MongoDB server if we started it."""
        if self.mongo_process:
            try:
                self.mongo_process.terminate()
                self.mongo_process.wait(timeout=5)
                print("Stopped MongoDB server")
            except Exception as e:
                print(f"Error stopping MongoDB server: {e}")
                try:
                    self.mongo_process.kill()
                except:
                    pass
    
    def is_connected(self):
        """Check if database connection is active."""
        return self.client is not None
    
    def add_image(self, filename, tags, prompt, seed=None, steps=None, width=None, height=None):
        """Add a new image entry to the database."""
        if not self.is_connected():
            print("⚠️ Database not connected, cannot register image")
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
            print(f"❌ Error adding image to database: {e}")
            return False
    
    def get_image(self, filename):
        """Get image details by filename."""
        if not self.is_connected():
            return None
            
        try:
            return self.collection.find_one({"filename": filename})
        except Exception as e:
            print(f"❌ Error retrieving image from database: {e}")
            return None
    
    def search_by_tags(self, tags, match_all=False, limit=100):
        """
        Search for images based on tags.
        
        Args:
            tags (list): List of tags to search for
            match_all (bool): If True, all tags must match. If False, any tag can match.
            limit (int): Maximum number of results to return
            
        Returns:
            list: List of matching image documents
        """
        if not self.is_connected() or not tags:
            return []
            
        try:
            # Build query based on match_all parameter
            if match_all:
                # All tags must be present
                query = {"tags": {"$all": [tag.strip() for tag in tags]}}
            else:
                # Any tag can match
                query = {"tags": {"$in": [tag.strip() for tag in tags]}}
            
            # Execute query
            cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            print(f"❌ Error searching images by tags: {e}")
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
            print(f"❌ Error performing text search: {e}")
            return []
    
    def get_all_images(self, limit=100):
        """Get all images, newest first."""
        if not self.is_connected():
            return []
            
        try:
            cursor = self.collection.find().sort("created_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            print(f"❌ Error retrieving all images from database: {e}")
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
            print(f"❌ Error retrieving unique tags: {e}")
            return []
    
    def delete_image(self, filename):
        """Delete an image entry from the database."""
        if not self.is_connected():
            return False
            
        try:
            result = self.collection.delete_one({"filename": filename})
            return result.deleted_count > 0
        except Exception as e:
            print(f"❌ Error deleting image from database: {e}")
            return False
    
    def close(self):
        """Close the database connection and stop MongoDB if we started it."""
        if self.client:
            self.client.close()
        
        # Stop MongoDB if we started it
        self._stop_mongodb_server()
