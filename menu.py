#!/usr/bin/env python
"""
Stock Images Generator Menu
A TUI (Text User Interface) for the stock images generator project.
"""

import sys
import subprocess
import os
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Button, Static, Input, Label
from textual.screen import Screen
from textual import events
from rich.panel import Panel
from rich.text import Text

# Import project modules
try:
    from db import ImageDatabase
except ImportError:
    print("Error: Could not import project modules. Make sure you're running from the project directory.")
    sys.exit(1)

class MenuHeader(Static):
    """A custom header for the menu screens."""
    
    def __init__(self, title: str):
        super().__init__()
        self.title = title
    
    def compose(self) -> ComposeResult:
        yield Static(f"[bold blue]{self.title}[/bold blue]", classes="header")

class MainMenu(Screen):
    """The main menu screen."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "app.pop_screen", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MenuHeader("Stock Images Generator")
        yield Container(
            Button("Generate Images", id="generate", variant="primary"),
            Button("Database Operations", id="database", variant="primary"),
            Button("Search Images", id="search", variant="primary"),
            Button("Exit", id="exit", variant="error"),
            id="menu-container",
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "generate":
            self.app.push_screen(GenerateMenu())
        elif button_id == "database":
            self.app.push_screen(DatabaseMenu())
        elif button_id == "search":
            self.app.push_screen(SearchMenu())
        elif button_id == "exit":
            self.app.exit()

class GenerateMenu(Screen):
    """The generate images menu screen."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "app.pop_screen", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MenuHeader("Generate Images")
        yield Container(
            Label("Number of Images:"),
            Input(placeholder="5", id="num_images"),
            Label("LM Studio Model (optional):"),
            Input(placeholder="Default from config", id="model"),
            Label("Workflow:"),
            Input(placeholder="flux_dev", id="workflow"),
            Button("Generate", id="start_generate", variant="success"),
            Button("Back", id="back", variant="primary"),
            id="generate-container",
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "start_generate":
            self.generate_images()
        elif button_id == "back":
            self.app.pop_screen()
    
    def generate_images(self) -> None:
        """Generate images with the specified parameters."""
        # Get input values
        num_images = self.query_one("#num_images").value or "5"
        model = self.query_one("#model").value
        workflow = self.query_one("#workflow").value or "flux_dev"
        
        # Build command
        cmd = ["python", "run_script.py", "generate.py", "--num", num_images, "--workflow", workflow]
        if model:
            cmd.extend(["--model", model])
        
        # Show processing screen
        self.app.push_screen(ProcessingScreen("Generating Images", cmd))

class DatabaseMenu(Screen):
    """The database operations menu screen."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "app.pop_screen", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MenuHeader("Database Operations")
        yield Container(
            Button("Trim Database", id="trim", variant="warning"),
            Button("Back", id="back", variant="primary"),
            id="database-container",
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "trim":
            # Show processing screen
            self.app.push_screen(ProcessingScreen("Trimming Database", ["python", "run_script.py", "db.py", "--trim"]))
        elif button_id == "back":
            self.app.pop_screen()

class SearchMenu(Screen):
    """The search images menu screen."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "app.pop_screen", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MenuHeader("Search Images")
        yield Container(
            Label("Enter tags to search for (comma-separated):"),
            Input(placeholder="subject:landscape, style:photorealistic", id="tags"),
            Button("Search", id="search_button", variant="success"),
            Button("Back", id="back", variant="primary"),
            id="search-container",
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "search_button":
            tags = self.query_one("#tags").value
            if not tags:
                self.app.push_screen(MessageScreen("Error", "Please enter at least one tag to search for."))
                return
            
            # Show processing screen
            self.app.push_screen(ProcessingScreen("Searching Images", ["python", "run_script.py", "search.py", "--tags", tags]))
        elif button_id == "back":
            self.app.pop_screen()

class ProcessingScreen(Screen):
    """A screen that shows processing status."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "app.pop_screen", "Back"),
    ]
    
    def __init__(self, title: str, command: list):
        super().__init__()
        self.title = title
        self.command = command
        self.process = None
        self.output = []
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MenuHeader(self.title)
        yield Container(
            Static(f"Running: {' '.join(self.command)}", id="command"),
            Static("", id="output"),
            Button("Back to Menu", id="back", variant="primary"),
            id="processing-container",
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Run the command when the screen is mounted."""
        self.run_command()
    
    def run_command(self) -> None:
        """Run the command and capture output."""
        try:
            # Set environment variables for proper encoding
            my_env = os.environ.copy()
            my_env["PYTHONIOENCODING"] = "utf-8"
            
            # Run the command and capture output
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=my_env,
                errors='replace'  # Replace invalid characters instead of crashing
            )
            
            # Read output line by line
            output_widget = self.query_one("#output")
            output_text = ""
            
            for line in process.stdout:
                # Replace any problematic characters
                clean_line = line.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                output_text += clean_line
                output_widget.update(output_text)
            
            process.wait()
            
            # Add completion message
            if process.returncode == 0:
                output_text += "\n\n[bold green]✅ Command completed successfully![/bold green]"
            else:
                output_text += f"\n\n[bold red]❌ Command failed with return code {process.returncode}[/bold red]"
            
            output_widget.update(output_text)
            
        except Exception as e:
            self.query_one("#output").update(f"[bold red]Error: {str(e)}[/bold red]")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()

class MessageScreen(Screen):
    """A screen that shows a message."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "app.pop_screen", "Back"),
    ]
    
    def __init__(self, title: str, message: str):
        super().__init__()
        self.title = title
        self.message = message
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MenuHeader(self.title)
        yield Container(
            Static(self.message),
            Button("OK", id="ok", variant="primary"),
            id="message-container",
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "ok":
            self.app.pop_screen()

class StockImagesApp(App):
    """The main application."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    .header {
        dock: top;
        height: 3;
        background: $primary-darken-2;
        color: $text;
        text-align: center;
        text-style: bold;
        padding: 1;
    }
    
    #menu-container {
        width: 100%;
        height: auto;
        align: center middle;
    }
    
    Button {
        width: 30;
        margin: 1 0;
    }
    
    #generate-container, #database-container, #search-container, #processing-container, #message-container {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 2;
    }
    
    Label {
        width: 100%;
        text-align: left;
        padding: 1 0 0 0;
    }
    
    Input {
        width: 100%;
        margin: 0 0 1 0;
    }
    
    #output {
        width: 100%;
        height: 20;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
        overflow-y: scroll;
    }
    """
    
    SCREENS = {
        "main": MainMenu(),
    }
    
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]
    
    def on_mount(self) -> None:
        """Set up the application when it starts."""
        self.push_screen("main")

def main():
    """Run the application."""
    app = StockImagesApp()
    app.run()

if __name__ == "__main__":
    main()
