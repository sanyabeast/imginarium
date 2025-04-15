# Stock Images Generator

![Stock Images Generator](https://img.shields.io/badge/Stock%20Images-Generator-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![LM Studio](https://img.shields.io/badge/LM%20Studio-Integrated-green)
![ComfyUI](https://img.shields.io/badge/ComfyUI-Integrated-green)
![MongoDB](https://img.shields.io/badge/MongoDB-Database-green)

A powerful tool for generating high-quality stock images using AI. This project combines LM Studio for prompt generation with ComfyUI for image creation, and includes a MongoDB database for image management.

## 🌟 Features

- **Tag-Based Generation**: Create images based on customizable tags like subject, mood, setting, and style
- **LM Studio Integration**: Generate detailed, creative prompts using advanced language models
- **ComfyUI Integration**: Create high-quality images using the powerful ComfyUI backend
- **Database Management**: Store and search images with MongoDB
- **Flexible Configuration**: Customize all aspects of the generation process
- **Command-Line Interface**: Easy-to-use CLI for generation and searching

## 📋 Requirements

- Python 3.9+
- LM Studio (for prompt generation)
- ComfyUI (for image generation)
- MongoDB (optional, for database features)

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/stock_images_generator.git
   cd stock_images_generator
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install and set up:
   - [LM Studio](https://lmstudio.ai/) - For prompt generation
   - [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - For image generation
   - [MongoDB](https://www.mongodb.com/try/download/community) (optional) - For database features

## ⚙️ Configuration

Edit the `config.yaml` file to customize your setup:

### Tags Configuration

Define the tags that will be used for image generation:

```yaml
tags:
  subject:
    - human_figure
    - group_of_people
    # Add more subjects...
  mood:
    - joyful
    - mysterious
    # Add more moods...
  # Add more categories...
```

### LM Studio Configuration

Configure the language model for prompt generation:

```yaml
lm_studio:
  model: "gemma-3-4b-it"
  prompt_template: |
    Generate a concise, stylized image prompt based on these tags: {tags}.
    # More template instructions...
```

### ComfyUI Configuration

Configure the image generation settings:

```yaml
comfy_ui:
  server_address: "127.0.0.1:8188"
  output_directory: "output_images"
  steps: 35
  width: 1536
  height: 1536
```

### Workflows

The project uses workflow files stored in the `workflows` directory. Each file contains a ComfyUI workflow JSON configuration:

- Default workflow: `flux_dev` (optimized for ComfyUI Flux model)
- To create a new workflow, add a file to the `workflows` directory
- Specify which workflow to use with the `-w` parameter when generating images

Example:
```bash
# Use a specific workflow
python generate.py -n 5 -w my_custom_workflow
```

### MongoDB Configuration

Configure the database settings:

```yaml
mongodb:
  data_dir: "./mongodb_data"
  db_name: "stock_images"
  collection: "images"
```

## 🖼️ Usage

### Generating Images

Generate stock images using the configured tags and settings:

```bash
# Generate 5 images (workflow parameter is required)
python generate.py -n 5 -w flux_dev

# Use a specific LM Studio model
python generate.py -n 3 -m "llama-3-8b-instruct" -w flux_dev

# Specify custom image dimensions
python generate.py -n 2 -w flux_dev -d 1920x1080

# Override the number of steps for generation
python generate.py -n 2 -w flux_dev -s 30

# Combine parameters
python generate.py -n 5 -m "gemma-3-4b-it" -w flux_dev -d 1024x1024 -s 40
```

Use `-h` or `--help` to see all available options:

```bash
python generate.py --help
```

### Managing the Database

Use the database management tools:

```bash
# View database information
python db.py --info

# List images in the database
python db.py --list

# Show database statistics
python db.py --stats

# Remove records for missing image files
python db.py --trim
```

### Searching Images

Search for images by tags:

```bash
# Search for images with specific tags
python search.py --tags subject:person mood:happy

# Search with text
python search.py --text "beach sunset"

# List recent images
python search.py --recent
```

## 📁 Project Structure

- `generate.py` - Main script for generating images
- `search.py` - Script for searching and browsing images
- `db.py` - Database management utilities
- `config.yaml` - Configuration file
- `output_images/` - Directory for generated images
- `mongodb_data/` - MongoDB database files
- `workflows/` - Directory for workflow files

## 🔧 Advanced Usage

### Custom Workflows

You can customize the ComfyUI workflow in the `config.yaml` file to use different models or generation techniques.

### External MongoDB

To use an external MongoDB instance, update the connection string in the `mongodb` section of the config.

## 📝 License

MIT License

Copyright (c) 2025 @sanyabeast

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
