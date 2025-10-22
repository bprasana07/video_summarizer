import logging
from flask import Flask, request, render_template_string
from Youtube_transcript_translate import (
    extract_video_id, get_video_title, get_transcript, 
    translate_transcript, format_transcript, summarize_basic, save_transcript
)

app = Flask(__name__)

# Logging configuration
logging.basicConfig(
    filename="/home/bprasana85/video_summarizer/flask_debug.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

@app.route("/", methods=["GET", "POST"])
def index():
    logging.debug("Index page accessed")
    summary = None
    filename = None
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        logging.debug(f"POST request received with URL: {url}")
        video_id = extract_video_id(url)
        logging.debug(f"Extracted video ID: {video_id}")
        if video_id:
            video_title = get_video_title(video_id)
            logging.debug(f"Video title: {video_title}")
            transcript_data, source_lang, needs_translation = get_transcript(video_id)
            if transcript_data:
                was_translated = False
                if source_lang not in ['en', 'unknown']:
                    transcript_data, was_translated = translate_transcript(transcript_data, source_lang)
                full_transcript = format_transcript(transcript_data)
                summary = summarize_basic(full_transcript)
                filename = save_transcript(
                    video_title, video_id, source_lang, was_translated, summary, full_transcript
                )
                logging.debug(f"Transcript saved to: {filename}")
            else:
                logging.warning("Transcript not fetched")
        else:
            logging.warning("Invalid video ID extracted")
    return render_template_string("<h1>Check logs for debug info</h1>")


if __name__ == "__main__":
    app.run(debug=True)