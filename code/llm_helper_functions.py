import requests
import json
import os
import base64
from pathlib import Path
import pandas as pd
import io
import time
import traceback

API_URL = "https://api.anthropic.com/v1/messages"
MAX_IMAGE_MB = 5 # Claude Limit 

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

    # For Rate Limiting Purposes 
    time.sleep(2)
    
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
    


def gravestone_desc(input_folder, prompts, columns, headers, debug=False, max_retries=3, retry_delay=2):
    """
    Uses the helper function to get all the names of the images, then calls claude with each prompt for each image.
    Puts all the information for each image in a row of a dataframe.
    
    Args:
        input_folder str: Folder path with the images
        prompts list(str): List of User-Specified Prompts for Claude
        columns list(str): Corresponding list of columns to store the results of the above prompts
        debug boolean: Debug mode. Turn on if you encounter errors and want to see the full debug message from anthropic. 
    Returns:
        df(DataFrame): Dataframe with the columns specified in columns
    """

    files = list_files_in_folder(input_folder)
    all_results = []

    for image in files:
        image_result = [image]
        image_path = input_folder + image

        for prompt in prompts:
            attempt = 0
            result_text = None

            # Error Handle if things go wrong, all data isn't lost
            while attempt < max_retries:
                try:
                    result = call_claude(prompt, headers=headers, image_path=image_path, debug=debug)
                    
                    if result is not None and 'content' in result and result['content']:
                        result_text = result['content'][0].get('text', '')
                        break  # success
                    else:
                        raise ValueError("Claude response malformed or empty")

                except Exception as e:
                    attempt += 1
                    if debug:
                        print(f"[Retry {attempt}/{max_retries}] Error with image '{image}' and prompt:\n{prompt}")
                        traceback.print_exc()
                    time.sleep(retry_delay)

            if result_text is None:
                result_text = f"[ERROR after {max_retries} attempts]"
                if debug:
                    print(f"[FAILED] Could not get result for image '{image}' and prompt:\n{prompt}")

            image_result.append(result_text)

        all_results.append(image_result)

    return pd.DataFrame(all_results, columns=columns)



def transcription_info(transcriptions, prompt, columns, headers, debug=False, max_retries=3, retry_delay=2):
    """
    Sends each transcription to Claude with the prompt, extracts comma-separated data, and returns a dataframe.

    Args:
        transcriptions (list[str]): List of transcription strings
        prompt (str): Prompt to prepend to each transcription
        columns (list[str]): Output column names (including transcription column at the end)
        headers (dict): Claude API headers
        debug (bool): Show debug info
        max_retries (int): Max retry attempts
        retry_delay (int): Delay between retries (seconds)

    Returns:
        pd.DataFrame: Results table
    """
    
    all_results = []

    for trans in transcriptions:
        attempt = 0
        result_list = None

        while attempt < max_retries:
            try:
                full_prompt = prompt + trans
                result = call_claude(full_prompt, headers=headers, debug=debug)

                if not result or 'content' not in result or not result['content']:
                    raise ValueError("Malformed Claude response or empty content")

                text = result['content'][0].get('text', '')
                result_list = [item.strip() for item in text.split(',')]

                # If we expect len(columns)-1 (excluding transcription), check shape
                expected_fields = len(columns) - 1  # transcription is added later
                if len(result_list) != expected_fields:
                    raise ValueError(f"Expected {expected_fields} fields, got {len(result_list)}")

                break  # success

            except Exception as e:
                attempt += 1
                if debug:
                    print(f"[Retry {attempt}/{max_retries}] Error with transcription:\n{trans}")
                    print(f"Error: {e}")  # Added to see the specific error
                    traceback.print_exc()
                time.sleep(retry_delay)

        if result_list is None:
            # Create a row that exactly matches the expected DataFrame structure
            result_list = [f"[ERROR after {max_retries} attempts]"] * (len(columns) - 1)

        # Ensure result_list + transcription matches column count exactly
        result_list.append(trans)  # Include transcription at the end
    
        # Safety check before adding to results
        if len(result_list) != len(columns):
            if debug:
                print(f"Warning: Row length mismatch. Expected {len(columns)}, got {len(result_list)}")
                print(f"Columns: {columns}")
                print(f"Result: {result_list}")
            # Truncate or pad to match expected length
            if len(result_list) > len(columns):
                result_list = result_list[:len(columns)]
            else:
                result_list.extend(['[MISSING]'] * (len(columns) - len(result_list)))
    
    all_results.append(result_list)

    return pd.DataFrame(all_results, columns=columns)