import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from googletrans import Translator
import requests
import re
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="YouTube Transcript Summarizer",
    page_icon="🎥",
    layout="wide"
)

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats"""
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
    """Fetch video title from YouTube using multiple methods"""
    # Method 1: Try oEmbed API (most reliable)
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(oembed_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            title = data.get('title', '')
            if title:
                # Clean title for filename
                clean_title = re.sub(r'[<>:"/\\|?*]', '', title)
                clean_title = clean_title.strip()[:100]  # Limit length
                return clean_title if clean_title else f"video_{video_id}"
    except Exception as e:
        pass
    
    # Method 2: Scrape from YouTube page
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # Try multiple title patterns
            patterns = [
                r'"title":"([^"]+)"',
                r'<title>([^<]+)</title>',
                r'<meta name="title" content="([^"]+)"'
            ]
            
            for pattern in patterns:
                title_match = re.search(pattern, response.text)
                if title_match:
                    title = title_match.group(1)
                    # Clean up title
                    title = title.replace(' - YouTube', '').strip()
                    # Handle unicode escapes
                    try:
                        title = title.encode().decode('unicode_escape')
                    except:
                        pass
                    # Clean title for filename
                    clean_title = re.sub(r'[<>:"/\\|?*]', '', title)
                    clean_title = clean_title.strip()[:100]
                    if clean_title:
                        return clean_title
    except Exception as e:
        pass
    
    # Fallback: Use video ID
    return f"video_{video_id}"

def get_transcript(video_id):
    """
    Fetch transcript from YouTube video.
    Compatible with the latest youtube-transcript-api versions (object-based return type).
    """
    try:
        api = YouTubeTranscriptApi()  # instantiate

        # Try English first
        try:
            transcript = api.fetch(video_id, languages=['en'])
            return transcript, 'en', False
        except Exception:
            pass

        # Try any available transcript
        try:
            transcript = api.fetch(video_id)
            return transcript, 'unknown', True
        except Exception:
            pass

        # Try to get list of available transcripts (new API naming)
        try:
            transcript_list = api.list(video_id)
            if not transcript_list:
                raise Exception("No transcripts available")

            # Look for English transcript
            english_transcript = next(
                (t for t in transcript_list if getattr(t, 'language_code', '') == 'en'),
                None
            )
            if english_transcript:
                return english_transcript.fetch(), 'en', False

            # Otherwise, pick the first available transcript
            first_transcript = transcript_list[0]
            transcript = first_transcript.fetch()
            return transcript, getattr(first_transcript, 'language_code', 'unknown'), True

        except Exception as e:
            st.error(f"Transcript fetch failed: {e}")
            return None, None, False

    except Exception as e:
        st.error(f"Error fetching transcript: {e}")
        return None, None, False


def translate_transcript(transcript_data, source_lang):
    """Translate transcript to English if not already in English"""
    if source_lang == 'en' or source_lang == 'unknown':
        return transcript_data, False
    
    try:
        translator = Translator()
        translated_data = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Translate in batches to avoid API limits
        batch_size = 10
        total_batches = len(transcript_data) // batch_size + 1
        
        for i in range(0, len(transcript_data), batch_size):
            batch = transcript_data[i:i+batch_size]
            texts = [item['text'] for item in batch]
            
            # Combine texts for translation
            combined_text = " ".join(texts)
            
            try:
                translated = translator.translate(combined_text, src=source_lang, dest='en')
                translated_text = translated.text
            except:
                # If translation fails, keep original
                translated_text = combined_text
            
            # Split back (approximate)
            translated_texts = translated_text.split(". ")
            
            for j, item in enumerate(batch):
                translated_item = item.copy()
                if j < len(translated_texts):
                    translated_item['text'] = translated_texts[j]
                else:
                    translated_item['text'] = item['text']
                translated_data.append(translated_item)
            
            # Update progress
            progress = min((i + batch_size) / len(transcript_data), 1.0)
            progress_bar.progress(progress)
            status_text.text(f"Translating: {int(progress * 100)}% complete")
        
        progress_bar.empty()
        status_text.empty()
        
        return translated_data, True
    except Exception as e:
        st.error(f"Translation error: {e}")
        return transcript_data, False

def format_transcript(transcript_data):
    """
    Convert transcript data to readable text.
    Works with both dict-based and object-based formats.
    """
    texts = []
    for item in transcript_data:
        if isinstance(item, dict):
            texts.append(item.get("text", ""))
        else:
            # Handle FetchedTranscriptSnippet objects (new API)
            texts.append(getattr(item, "text", ""))
    return " ".join(texts)

def summarize_basic(text):
    """Basic summarization without AI (extracts key sentences)"""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    # Take first, middle, and last portions
    total = len(sentences)
    if total <= 10:
        key_sentences = sentences
    else:
        key_sentences = (
            sentences[:3] +  # Beginning
            sentences[total//2-2:total//2+2] +  # Middle
            sentences[-3:]  # End
        )
    
    summary = "\n\n".join(key_sentences)
    
    # Add basic structure
    return f"""**Key Points from Transcript:**

{summary}

**Note:** This is a basic summary. Enable OpenAI in settings for a more detailed analysis with main topics, intentions, and key takeaways."""

def summarize_with_openai(text, api_key):
    """Summarize using OpenAI GPT"""
    try:
        import openai
        
        client = openai.OpenAI(api_key=api_key)
        
        prompt = f"""Analyze and summarize the following transcript. Provide:

1. **Main Topic/Theme**: What is this video about?

2. **Key Points**: List the main arguments, ideas, or information discussed (use bullet points)

3. **Intentions/Purpose**: What is the speaker trying to achieve or communicate?

4. **Important Details**: Any specific facts, examples, or data mentioned

5. **Conclusion/Takeaways**: What should viewers remember?

Transcript:
{text[:15000]}
"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates clear, structured summaries of video transcripts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"OpenAI summarization error: {e}")
        return summarize_basic(text)

def save_transcript(video_title, video_id, source_lang, was_translated, summary, full_transcript):
    """Save transcript to file with video name"""
    try:
        # Create transcripts directory if it doesn't exist
        os.makedirs("transcripts", exist_ok=True)
        
        # Create filename with video title and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcripts/{video_title}_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"YouTube Video: {video_title}\n")
            f.write(f"Video ID: {video_id}\n")
            f.write(f"URL: https://www.youtube.com/watch?v={video_id}\n")
            f.write(f"Original Language: {source_lang}\n")
            f.write(f"Translated to English: {was_translated}\n")
            f.write(f"Date Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("=" * 80 + "\n")
            f.write("SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            f.write(summary + "\n\n")
            f.write("=" * 80 + "\n")
            f.write("FULL TRANSCRIPT\n")
            f.write("=" * 80 + "\n\n")
            f.write(full_transcript)
        
        return filename
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

# Streamlit App UI
def main():
    st.title("🎥 YouTube Transcript Extractor & Summarizer")
    st.markdown("Extract, translate, and summarize YouTube video transcripts with AI-powered analysis")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        use_openai = st.checkbox("Use OpenAI for Advanced Summary", value=False)
        
        openai_key = ""
        if use_openai:
            openai_key = st.text_input("OpenAI API Key", type="password", help="Get your API key from https://platform.openai.com/")
        
        st.markdown("---")
        st.markdown("### 📁 Saved Transcripts")
        st.info("All transcripts are automatically saved in the 'transcripts' folder with the video name")
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        youtube_url = st.text_input(
            "Enter YouTube URL or Video ID",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Paste any YouTube video URL or just the video ID"
        )
    
    with col2:
        st.write("")
        st.write("")
        process_button = st.button("🚀 Process Video", type="primary", use_container_width=True)
    
    if process_button and youtube_url:
        # Extract video ID
        video_id = extract_video_id(youtube_url)
        
        if not video_id:
            st.error("❌ Invalid YouTube URL or Video ID")
            return
        
        with st.spinner("Fetching video information..."):
            video_title = get_video_title(video_id)
            st.success(f"✅ Video: **{video_title}**")
        
        # Display video
        st.video(f"https://www.youtube.com/watch?v={video_id}")
        
        # Get transcript
        with st.spinner("📝 Fetching transcript..."):
            transcript_data, source_lang, needs_translation = get_transcript(video_id)
        
        if not transcript_data:
            st.error("❌ Could not fetch transcript. The video may not have captions available.")
            return
        
        st.info(f"Original language: **{source_lang}**")
        
        # Translate if needed
        was_translated = False
        if source_lang not in ['en', 'unknown']:
            with st.spinner(f"🌐 Translating from {source_lang} to English..."):
                transcript_data, was_translated = translate_transcript(transcript_data, source_lang)
            
            if was_translated:
                st.success("✅ Translation completed!")
        
        # Format transcript
        full_transcript = format_transcript(transcript_data)
        
        # Summarize
        with st.spinner("🤖 Generating summary..."):
            if use_openai and openai_key:
                summary = summarize_with_openai(full_transcript, openai_key)
            else:
                summary = summarize_basic(full_transcript)
                if not use_openai:
                    st.info("💡 Using basic summarization. Enable OpenAI in settings for better results.")
        
        # Save transcript
        with st.spinner("💾 Saving transcript..."):
            filename = save_transcript(video_title, video_id, source_lang, was_translated, summary, full_transcript)
        
        if filename:
            st.success(f"✅ Transcript saved to: `{filename}`")
        
        # Display results
        st.markdown("---")
        
        # Summary section
        st.header("📋 Summary")
        st.markdown(summary)
        
        # Transcript section
        st.markdown("---")
        st.header("📄 Full Transcript")
        
        with st.expander("Click to view full transcript", expanded=False):
            st.text_area("Transcript", full_transcript, height=400, label_visibility="collapsed")
        
        # Download button
        st.download_button(
            label="⬇️ Download Transcript",
            data=full_transcript,
            file_name=f"{video_title}_transcript.txt",
            mime="text/plain"
        )

if __name__ == "__main__":
    main()