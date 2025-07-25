import requests
import json
import os
import base64
from pathlib import Path
import pandas as pd
import io

API_URL = "https://api.anthropic.com/v1/messages"
MAX_IMAGE_MB = 5

def get_api_key(file): 
    """
    Get the API Key
    
    Args:
        file (str): Path to the credentials file
    
    Returns:
        str: API Key
    """
    with open(file, 'r') as f:
        return f.read().strip()
    
def list_files_in_folder(folder_path):
    """
    Get the names of all the files in a folder
    
    Args:
        folder_path (str): Path to folder
    
    Returns:
        list[str]: list of file names
    """
    try:
        files = os.listdir(folder_path)
        
        # Filter out directories, keeping only files
        file_names = [f for f in files if os.path.isfile(os.path.join(folder_path, f))]
        
        return file_names
    
    # Errors
    except FileNotFoundError:
        print(f"The folder at {folder_path} does not exist.")
        return []
    except PermissionError:
        print(f"Permission denied to access the folder at {folder_path}.")
        return []

    
def debug_request(data, headers):
    """Print request details for debugging"""
    print("=== DEBUG INFO ===")
    print(f"URL: {API_URL}")
    print(f"Method: POST")
    print("Headers:")
    for key, value in headers.items():
        if key == "x-api-key":
            print(f"  {key}: {value[:10]}...")  # Only show first 10 chars
        else:
            print(f"  {key}: {value}")
    print(f"Data keys: {list(data.keys())}")
    print(f"Model: {data.get('model')}")
    print(f"Message type: {type(data.get('messages', [{}])[0].get('content'))}")
    print("===================")


def encode_image(image_path):
    """
    Encode an image to base64 string
    
    Args:
        image_path (str): Path to the image file
    
    Returns:
        tuple: (base64_string, media_type) or (None, None) if error
    """
    try:
        # Check if file size is less than 5MB
        file_size_bytes = os.path.getsize(image_path)
        if file_size_bytes > MAX_IMAGE_MB * 1024 * 1024:
            raise ValueError(f"Image file is too large: {file_size_bytes / (1024*1024):.2f}MB (limit is {MAX_IMAGE_MB}MB)")
        
        # Get file extension to determine media type
        file_ext = Path(image_path).suffix.lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        
        if file_ext not in media_type_map:
            print(f"Unsupported image format: {file_ext}")
            return None, None
        
        with open(image_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string, media_type_map[file_ext]
    
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None, None


def call_claude(prompt, headers, image_path = None, model="claude-sonnet-4-20250514", debug="False"):
    """
    Call Claude API with a message and optional image
    
    Args:
        message (str): The message to send to Claude
        image_path (str): Path to image file (optional)
        model (str): The model to use (default: claude-sonnet-4-20250514)
    
    Returns:
        dict: API response
    """
    
    # Set content to the prompt
    content = [{"type": "text", "text": prompt}]

    # Add and encode an image if present 
    if image_path:
        encoded_image, media_type = encode_image(image_path)
        if encoded_image:
            content.insert(0, {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": encoded_image
                }
            })
        else:
            print("Failed to encode image, continuing with text only")
    
    # Query to Claude
    data = {
        "model": model,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ]
    }

    # Error Handleing and Debug Mode
    if debug:
        debug_request(data, headers)
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        
        if debug:
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
        
        # Print response content for debugging
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return None