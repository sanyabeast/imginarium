# Imginarium

![Imginarium](https://img.shields.io/badge/Imginarium-AI%20Image%20Generator-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![LM Studio](https://img.shields.io/badge/LM%20Studio-Integrated-green)
![ComfyUI](https://img.shields.io/badge/ComfyUI-Integrated-green)
![MongoDB](https://img.shields.io/badge/MongoDB-Database-green)

A powerful tool for generating high-quality images using AI. This project combines LM Studio for prompt generation with ComfyUI for image creation, and includes a MongoDB database for image management.

## 🌟 Features

- **Multiple Configuration Profiles**: Choose between different generation styles (stock, art, avantgarde, etc.)
- **Dynamic Configuration Detection**: Automatically detects all config files in the configs directory
- **Tag-Based Generation**: Create images based on customizable tags like subject, mood, setting, and style
- **LM Studio Integration**: Generate detailed, creative prompts using advanced language models
- **ComfyUI Integration**: Create high-quality images using the powerful ComfyUI backend
- **Database Management**: Store and search images with MongoDB
- **Flexible Configuration**: Customize all aspects of the generation process
- **User-Friendly Menu Interface**: Simple numbered menu system for easy navigation
- **Default Workflow Support**: Each configuration can specify its own default workflow
- **Multiple Workflow Support**: Use different ComfyUI workflows for various generation techniques
- **Workflow Validation**: Automatic validation of workflow files for required placeholders
- **Placeholder System**: Use placeholders in workflows for dynamic content
- **PNG Metadata**: Embedded PNG metadata for portability
- **Metadata Extraction**: Extract metadata from generated PNG images
- **Improved Parameter Handling**: Config defaults are properly respected when custom parameters are skipped

## 📋 Requirements

- Python 3.9+
- LM Studio (for prompt generation)
- ComfyUI (for image generation)
- MongoDB (optional, for database features)

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
   - [MongoDB](https://www.mongodb.com/try/download/community) (optional) - For database features

## 📋 Using the Menu Interface

The project includes a user-friendly menu interface that makes it easy to use all features without remembering command-line parameters.

To start the menu:
```bash
menu.bat
```

The menu provides the following options:

### Configuration Selection
- The menu dynamically lists all available configurations from the `configs` directory
- Select a configuration to use for all operations

### Main Menu
- **[1] Generate Images**: Create new images with default or custom settings
- **[2] Search Images**: Search for images by tags or browse all images
- **[3] Database Management**: View database stats or trim unused records
- **[4] Setup/Update Dependencies**: Install or update project dependencies
- **[5] Change Configuration**: Switch between different configuration profiles
- **[6] Exit**: Exit the program

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
  default_workflow: "flux_dev"  # Default workflow to use for this config
  steps: 35
  width: 1536
  height: 1536
```

When generating images with custom parameters but choosing to skip the parameter selection, the system will now properly use these config defaults rather than falling back to hardcoded values.

### Output Directory Structure

Generated images are automatically saved to:
```
output/{config_name}/
```

For example:
- `output/stock/` - Images generated with the stock configuration
- `output/art/` - Images generated with the art configuration
- `output/avantgarde/` - Images generated with the avantgarde configuration

## 🖼️ Command-Line Usage

While the menu interface is recommended for most users, you can also use the command-line interface for more advanced usage:

### Generating Images

Generate images using the configured tags and settings:

```bash
# Generate 5 images using the default workflow from the stock config
python generate.py -n 5 -c stock

# Specify a custom workflow instead of using the default
python generate.py -n 5 -w flux_dev -c stock

# Use a specific LM Studio model with the art config
python generate.py -n 3 -m "llama-3-8b-instruct" -c art

# Specify custom image dimensions
python generate.py -n 2 -c stock -d 1920x1080

# Override the number of steps for generation
python generate.py -n 2 -c art -s 30

# Combine parameters
python generate.py -n 5 -m "gemma-3-4b-it" -w flux_dev -c stock -d 1024x1024 -s 40
```

Use `-h` or `--help` to see all available options:

```bash
python generate.py --help
```

### Managing the Database

Use the database management tools:

```bash
# View database information for the stock config
python db.py --info -c stock

# List images in the art collection
python db.py --list -c art

# Show database statistics for the stock config
python db.py --stats -c stock

# Trim database records for missing files in the art config
python db.py --trim -c art
```

## 📁 Project Structure

- `generate.py` - Main script for generating images
- `search.py` - Script for searching and browsing images
- `db.py` - Database management utilities
- `configs/` - Directory for configuration files
- `output/` - Directory for generated images
- `mongodb_data/` - MongoDB database files
- `workflows/` - Directory for workflow files

## 🔧 Advanced Usage

### Custom Workflows

You can create custom ComfyUI workflows and specify them in your configuration files. Each config can have its own default workflow.

### Adding New Configurations

To add a new configuration:

1. Create a new YAML file in the `configs` directory (e.g., `custom.yaml`)
2. Define your tags, prompt template, and ComfyUI settings
3. Specify a default workflow in the ComfyUI section
4. The new configuration will automatically appear in the menu

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
