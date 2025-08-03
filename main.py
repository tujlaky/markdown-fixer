import sys
import requests
import re
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    print("API_KEY is not set. Please set it in the .env file.")
    sys.exit(1)


def extract_video_id_from_youtube_link(url):
    # Dummy implementation for extracting video ID
    # eg: https://youtu.be/eE6yvtKLwvk?si=s8AQ1Wh0w9jk9rVE
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "youtube.com/watch?v=" in url:
        return url.split("youtube.com/watch?v=")[1].split("&")[0]
    elif "youtube.com/embed/" in url:
        return url.split("youtube.com/embed/")[1].split("?")[0]
    elif "youtube.com/v/" in url:
        return url.split("youtube.com/v/")[1].split("?")[0]
    elif "youtube.com/shorts/" in url:
        return url.split("youtube.com/shorts/")[1].split("?")[0]
    elif "youtube.com/live/" in url:
        # Handle YouTube live URLs
        return url.split("youtube.com/live/")[1].split("?")[0]
    else:
        return None


def get_video_title(video_id):
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            return data["items"][0]["snippet"]["title"]
        else:
            print(f"No video found with ID: {video_id}")
            return None
    else:
        print(f"Failed to fetch video details: {response.status_code} - {response.text}")
        return None


def get_url_title(url):
    """
    Download a webpage and extract its title from the HTML header
    """
    try:
        # Send a request with a user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract the title
            title_tag = soup.find('title')
            
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
                return title
            else:
                print(f"No title found for URL: {url}")
                # Use domain name as fallback title
                domain = urlparse(url).netloc
                return f"Link to {domain}"
        else:
            print(f"Failed to fetch URL: {response.status_code}")
            # Use domain name as fallback title
            domain = urlparse(url).netloc
            return f"Link to {domain}"
    except Exception as e:
        print(f"Error fetching URL title: {str(e)}")
        # Use domain name as fallback title
        domain = urlparse(url).netloc
        return f"Link to {domain}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <markdown_file_path>")
        sys.exit(1)

    input_path = sys.argv[1]

    # Check if the input is a file or a URL
    if os.path.isfile(input_path):
        # Process markdown file
        try:
            with open(input_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Find all YouTube links in the content
            # Pattern to match YouTube URLs
            youtube_patterns = [
                r'(https?://(?:www\.)?youtu\.be/[a-zA-Z0-9_-]+(?:\?[^\s\?]*(?:\?[^\s\?]*)*)?)',
                r'(https?://(?:www\.)?youtube\.com/live/[a-zA-Z0-9_-]+(?:\?[^\s\?]*(?:\?[^\s\?]*)*)?)',
                r'(https?://(?:www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]+(?:&[^\s\?]*)*)',
                r'(https?://(?:www\.)?youtube\.com/embed/[a-zA-Z0-9_-]+(?:\?[^\s\?]*(?:\?[^\s\?]*)*)?)',
                r'(https?://(?:www\.)?youtube\.com/v/[a-zA-Z0-9_-]+(?:\?[^\s\?]*(?:\?[^\s\?]*)*)?)',
                r'(https?://(?:www\.)?youtube\.com/shorts/[a-zA-Z0-9_-]+(?:\?[^\s\?]*(?:\?[^\s\?]*)*)?)'
            ]

            modified_content = content
            total_replacements = 0
            processed_urls = set()  # Keep track of already processed URLs
            
            # First find all YouTube links
            youtube_urls = []
            for pattern in youtube_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    youtube_url = match.group(0)
                    if youtube_url not in processed_urls:
                        youtube_urls.append((youtube_url, match.start()))
            
            # Then find all URLs that are not already identified as YouTube links
            # General URL pattern - avoiding common file extensions that aren't web pages
            general_url_pattern = r'(https?://(?:www\.)?[^\s\)\]\"\'\>]+(?<!\.jpg|\.png|\.gif|\.pdf|\.zip|\.mp3|\.mp4))'
            general_matches = re.finditer(general_url_pattern, content)
            
            # Store all replacements to make at once
            replacements = []
            
            for match in general_matches:
                url = match.group(0)
                start_pos = match.start()
                
                # Skip if this URL is already identified as a YouTube URL or already processed
                if url in processed_urls or any(youtube_url[0] == url for youtube_url in youtube_urls):
                    continue
                
                # Check if the URL is already part of a markdown link
                preceding_text = content[:start_pos]
                following_text = content[start_pos + len(url):]
                
                is_in_markdown_link = False
                if re.search(r'\]\([^\)]*$', preceding_text) and re.search(r'^\s*\)', following_text):
                    is_in_markdown_link = True
                
                if not is_in_markdown_link:
                    # Process non-YouTube URL
                    processed_urls.add(url)  # Mark as processed
                    title = get_url_title(url)
                    if title:
                        markdown_link = f"[{title}]({url})"
                        replacements.append((url, markdown_link))
                        print(f"Replaced generic URL: {url} → {markdown_link}")
            
            # Track URLs we've already converted to markdown to avoid nested replacements
            markdown_replacements = {}
            
            # Process general URLs
            for url, markdown_link in replacements:
                # Use regex for more precise replacement (only replace standalone URLs, not those in markdown)
                pattern = re.compile(re.escape(url) + r'(?!\))')
                modified_content = pattern.sub(markdown_link, modified_content)
                total_replacements += 1
                markdown_replacements[url] = markdown_link
            
            # Clear replacements for YouTube links
            replacements = []
            
            # Now process YouTube links
            for youtube_url, start_pos in youtube_urls:
                if youtube_url in processed_urls:
                    continue
                
                # If we can't find the URL in the content anymore, it might be already replaced
                if youtube_url not in modified_content:
                    continue
                
                # Find all occurrences of this URL in the modified content
                for match in re.finditer(re.escape(youtube_url), modified_content):
                    new_pos = match.start()
                    
                    # Check if this URL is already part of a markdown link
                    preceding_text = modified_content[:new_pos]
                    following_text = modified_content[new_pos + len(youtube_url):]
                    
                    # Check for markdown pattern
                    if re.search(r'\]\([^\)]*$', preceding_text) and re.search(r'^\s*\)', following_text):
                        print(f"Skipped: {youtube_url} (already in a markdown link)")
                        continue
                    
                    # Process YouTube URL
                    processed_urls.add(youtube_url)  # Mark as processed
                    video_id = extract_video_id_from_youtube_link(youtube_url)
                    
                    if video_id:
                        video_title = get_video_title(video_id)
                        
                        if video_title:
                            markdown_link = f"[{video_title}](https://www.youtube.com/watch?v={video_id})"
                            replacements.append((youtube_url, markdown_link))
                            markdown_replacements[youtube_url] = markdown_link
                            print(f"Replaced YouTube: {youtube_url} → {markdown_link}")
                            break  # Only add this URL once
            
            # Apply YouTube replacements using regex for more precise replacements
            for url, markdown_link in replacements:
                # This pattern ensures we only replace URLs that aren't already in a markdown link
                pattern = re.compile(r'(?<!\]\()' + re.escape(url) + r'(?!\))')
                modified_content = pattern.sub(markdown_link, modified_content)
                total_replacements += 1
            
            # Write the modified content back to the file
            if total_replacements > 0:
                with open(input_path, 'w', encoding='utf-8') as file:
                    file.write(modified_content)
                print(f"Successfully replaced {total_replacements} YouTube links in {input_path}")
            else:
                print(f"No YouTube links found in {input_path}")

        except Exception as e:
            print(f"Error processing the markdown file: {e}")
            sys.exit(1)
    else:
        print(f"Input path '{input_path}' is not a valid file.")
        sys.exit(1)

if __name__ == "__main__":
    main()
    sys.exit(0) 