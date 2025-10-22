from youtube_transcript_api import YouTubeTranscriptApi
from googletrans import Translator
import requests
import re
import os
from datetime import datetime

def extract_video_id(url):
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_video_title(video_id):
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(oembed_url, timeout=10)
        if response.status_code == 200:
            title = response.json().get('title', '')
            if title:
                return re.sub(r'[<>:"/\\|?*]', '', title).strip()[:100]
    except:
        pass
    # Fallback: scrape
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            patterns = [
                r'"title":"([^"]+)"',
                r'<title>([^<]+)</title>',
                r'<meta name="title" content="([^"]+)"'
            ]
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    title = match.group(1).replace(' - YouTube', '').strip()
                    return re.sub(r'[<>:"/\\|?*]', '', title).strip()[:100]
    except:
        pass
    return f"video_{video_id}"

def get_transcript(video_id):
    api = YouTubeTranscriptApi()
    try:
        transcript = api.fetch(video_id, languages=['en'])
        return transcript, 'en', False
    except:
        try:
            transcript = api.fetch(video_id)
            return transcript, 'unknown', True
        except:
            return None, None, False

def translate_transcript(transcript_data, source_lang):
    if source_lang == 'en' or source_lang == 'unknown':
        return transcript_data, False
    translator = Translator()
    translated_data = []
    batch_size = 10
    for i in range(0, len(transcript_data), batch_size):
        batch = transcript_data[i:i+batch_size]
        texts = [item['text'] for item in batch]
        combined_text = " ".join(texts)
        try:
            translated = translator.translate(combined_text, src=source_lang, dest='en')
            translated_text = translated.text
        except:
            translated_text = combined_text
        translated_texts = translated_text.split(". ")
        for j, item in enumerate(batch):
            t_item = item.copy()
            if j < len(translated_texts):
                t_item['text'] = translated_texts[j]
            else:
                t_item['text'] = item['text']
            translated_data.append(t_item)
        print(f"Translating: {min(i + batch_size, len(transcript_data))}/{len(transcript_data)} lines", end='\r')
    print("\nTranslation complete!")
    return translated_data, True

def format_transcript(transcript_data):
    texts = []
    for item in transcript_data:
        if isinstance(item, dict):
            texts.append(item.get("text", ""))
        else:
            texts.append(getattr(item, "text", ""))
    return " ".join(texts)

def summarize_basic(text):
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    total = len(sentences)
    if total <= 10:
        key_sentences = sentences
    else:
        key_sentences = sentences[:3] + sentences[total//2-2:total//2+2] + sentences[-3:]
    summary = "\n\n".join(key_sentences)
    return f"Key Points from Transcript:\n\n{summary}\n\n(Note: Basic summary, no AI.)"

def save_transcript(video_title, video_id, source_lang, was_translated, summary, full_transcript, dir_path=None):
    if dir_path is None:
        dir_path = os.path.join(os.getcwd(), "transcripts")
    os.makedirs(dir_path, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(dir_path, f"{video_title}_{timestamp}.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"YouTube Video: {video_title}\n")
        f.write(f"Video ID: {video_id}\n")
        f.write(f"URL: https://www.youtube.com/watch?v={video_id}\n")
        f.write(f"Original Language: {source_lang}\n")
        f.write(f"Translated to English: {was_translated}\n")
        f.write(f"Date Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("=" * 80 + "\nSUMMARY\n" + "=" * 80 + "\n\n")
        f.write(summary + "\n\n" + "=" * 80 + "\nFULL TRANSCRIPT\n" + "=" * 80 + "\n\n")
        f.write(full_transcript)
    return filename

# Main console app
def main():
    youtube_url = input("Enter YouTube URL or Video ID: ").strip()
    video_id = extract_video_id(youtube_url)
    if not video_id:
        print("Invalid URL or Video ID")
        return
    print("Fetching video info...")
    video_title = get_video_title(video_id)
    print(f"Video title: {video_title}")
    transcript_data, source_lang, needs_translation = get_transcript(video_id)
    if not transcript_data:
        print("Could not fetch transcript.")
        return
    print(f"Original language: {source_lang}")
    was_translated = False
    if source_lang not in ['en', 'unknown']:
        transcript_data, was_translated = translate_transcript(transcript_data, source_lang)
    full_transcript = format_transcript(transcript_data)
    summary = summarize_basic(full_transcript)
    filename = save_transcript(video_title, video_id, source_lang, was_translated, summary, full_transcript)
    print(f"Transcript saved to: {filename}")
    print("\nSummary:\n")
    print(summary)

if __name__ == "__main__":
    main()