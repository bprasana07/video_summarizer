import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Streamlit UI
st.title("YouTube Video Summarizer")
st.write("Enter a YouTube video URL to fetch transcript and summarize it.")

# Input box for YouTube URL
video_url = st.text_input("YouTube Video URL")

def extract_video_id(url: str) -> str:
    """
    Extract the video ID from a YouTube URL.
    Supports full URLs, shortened URLs, or just ID.
    """
    url = url.strip()  # remove whitespace
    # Regular expression to find the v= parameter
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
    elif len(url) == 11:  # if user directly enters the video ID
        return url
    else:
        return None

# Submit button
if st.button("Summarize Video"):

    video_id = extract_video_id(video_url)
    if not video_id:
        st.error("Invalid YouTube URL or video ID.")
    else:
        st.info(f"Processing video: {video_id} ...")

        # Fetch transcript
        try:
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id)
            text = " ".join([t.text for t in transcript])

            # Save transcript file
            transcript_file = f"transcript_{video_id}.txt"
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write(text)
            st.success(f"Transcript saved as {transcript_file}")

            # Summarize with LLM
            summary = llm.predict(
                f"Summarize the following YouTube transcript concisely, highlighting key points:\n\n{text}"
            )

            st.subheader("Video Summary")
            st.write(summary)

            # Save summary file
            summary_file = f"summary_{video_id}.txt"
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(summary)
            st.success(f"Summary saved as {summary_file}")

        except Exception as e:
            st.error(f"Error fetching transcript: {e}")