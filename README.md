# Imginarium

![Imginarium](https://img.shields.io/badge/Imginarium-AI%20Image%20Generator-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![LM Studio](https://img.shields.io/badge/LM%20Studio-Integrated-green)
![ComfyUI](https://img.shields.io/badge/ComfyUI-Integrated-green)

A powerful tool for generating high-quality images using AI. This project combines LM Studio for prompt generation with ComfyUI for image creation, with embedded metadata for easy searching.

## 🌟 Features

- **Multiple Configuration Profiles**: Choose between different generation styles (stock, art, avantgarde, etc.)
- **Dynamic Configuration Detection**: Automatically detects all config files in the configs directory
- **Tag-Based Generation**: Create images based on customizable tags like subject, mood, setting, and style
- **LM Studio Integration**: Generate detailed, creative prompts using advanced language models
- **ComfyUI Integration**: Create high-quality images using the powerful ComfyUI backend
- **Metadata-Based Search**: Search for images using embedded PNG metadata
- **HTTP Server API**: Search and retrieve images across configurations via a RESTful API
- **Flexible Configuration**: Customize all aspects of the generation process
- **User-Friendly Menu Interface**: Simple numbered menu system for easy navigation
- **Default Workflow Support**: Each configuration can specify its own default workflow
- **Multiple Workflow Support**: Use different ComfyUI workflows for various generation techniques
- **Workflow Validation**: Automatic validation of workflow files for required placeholders
- **Placeholder System**: Use placeholders in workflows for dynamic content
- **PNG Metadata**: Embedded PNG metadata for portability and searchability
- **Metadata Extraction**: Extract metadata from generated PNG images
- **Improved Parameter Handling**: Config defaults are properly respected when custom parameters are skipped
- **Fuzzy Search**: Find images with similar descriptions using fuzzy matching

## 📋 Requirements

- Python 3.9+
- LM Studio (for prompt generation)
- ComfyUI (for image generation)

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/imginarium.git
   cd imginarium
   ```

2. Run the installer script:
   ```bash
   # On Windows
   install.bat
   ```

3. Install and set up:
   - [LM Studio](https://lmstudio.ai/) - For prompt generation
   - [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - For image generation

## 📋 Using the Menu Interface

The project includes a user-friendly menu interface that makes it easy to use all features without remembering command-line parameters.

To start the menu:
```bash
menu.bat
```

The menu provides the following options:

### Main Menu
- **[1] Generate Images**: Create new images with default or custom settings
- **[2] Search Images**: Search for images using text queries
- **[3] Start Search Server**: Launch the HTTP search API server
- **[4] Setup/Update Dependencies**: Install or update project dependencies
- **[5] Exit**: Exit the program

### Generate Images
When selecting "Generate Images", you'll first choose a configuration profile, then proceed to the generation menu:
- **[1] Generate with default settings**: Quick generation with default parameters
- **[2] Custom generation**: Specify custom parameters like number of images, dimensions, etc.

### Search Images
The search feature allows you to find images using text queries:
- Enter your search terms
- Specify the maximum number of results to show
- Results will display with detailed metadata

### Start Search Server
Launch an HTTP server that provides a search API:
- Enter a port number (default: 5666)
- The server will start and provide endpoints for searching images

## 🌐 HTTP Search API

The project includes an HTTP server that allows searching for images using their embedded metadata:

### Starting the Server

Start the server using the menu interface or directly:
```bash
python search.py --server [PORT]
```

The default port is 5666 if not specified.

### API Endpoints

#### Search Images

**GET /search**

Search for images using query parameters:

```
/search?query=modern+home+interior&limit=5&threshold=0.6
```

**Parameters:**

- `query`: Text to search for in image descriptions and tags (required)
- `limit`: Maximum number of images to return (default: 5)
- `threshold`: Fuzzy matching threshold from 0.0 to 1.0 (default: 0.5)
  - Lower values (e.g., 0.3) = more lenient matching, more results
  - Higher values (e.g., 0.8) = stricter matching, fewer but more relevant results

**Response:**

The API returns a list of absolute paths to matching images:
```json
[
  "G:\\Projects\\experiments\\imginarium\\output\\stock\\image_20250418_123456.png",
  "G:\\Projects\\experiments\\imginarium\\output\\art\\image_20250418_234567.png"
]
```

#### Get Statistics

**GET /stats**

Get statistics about the image collection:

```
/stats
```

**Response:**

```json
{
  "total_images": 459,
  "configs": {
    "anime": 24,
    "art": 109,
    "avantgarde": 145,
    "cctv": 5,
    "gamedev": 10,
    "retrofuture": 59,
    "spooky": 61,
    "stock": 46
  }
}
```

## ⚙️ Configuration

The project supports multiple configuration profiles in the `configs` directory:

- **stock.yaml**: Configuration for standard stock image generation
- **art.yaml**: Configuration for artistic/creative image generation
- **avantgarde.yaml**: Configuration for experimental/avant-garde image generation
- **Add your own**: Create new .yaml files in the configs directory to add more profiles

Each configuration file defines:

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
    You are a creative visual assistant generating prompts for a stock image AI system.
    # More template instructions...
```

### ComfyUI Configuration

Configure the image generation settings:

```yaml
comfy_ui:
  server_address: "127.0.0.1:8188"
  client_id: "1234abcd-1234-abcd-1234-abcd1234abcd"  # Auto-generated if not provided
  output_directory: "output/stock"
  default_workflow: "flux_dev"
  width: 1536
  height: 1536
  steps: 35
```

## 📝 Command Line Usage

While the menu interface is recommended, you can also use the command line directly:

### Generate Images

```bash
python generate.py --num 5 --config stock --workflow flux_dev --dimensions 1024x1024 --steps 30
```

### Search Images

```bash
python search.py -q "forest landscape" -l 10 -t 0.7
```

### Start Search Server

```bash
python search.py --server 8080
```

## 📂 Project Structure

- **configs/**: Configuration files for different generation styles
- **workflows/**: ComfyUI workflow files
- **output/**: Generated images, organized by configuration
- **menu.bat**: User-friendly menu interface
- **generate.py**: Image generation script
- **search.py**: Image search script
- **install.bat**: Installation and dependency setup script

## 📜 License

MIT License

Copyright (c) 2025

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
