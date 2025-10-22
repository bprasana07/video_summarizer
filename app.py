from flask import Flask, request, render_template_string
from Youtube_transcript_translate import (
    extract_video_id, get_video_title, get_transcript, 
    translate_transcript, format_transcript, summarize_basic, save_transcript
)

import os

app = Flask(__name__)

TRANSCRIPTS_DIR = "/home/bprasana85/video_summarizer/transcripts"
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

HTML_TEMPLATE = """
<!doctype html>
<title>YouTube Transcript Summarizer</title>
<h1>YouTube Transcript Summarizer</h1>
<form method=post>
  YouTube URL or Video ID: <input type=text name=url>
  <input type=submit value=Submit>
</form>
{% if summary %}
<h2>Summary:</h2>
<pre>{{ summary }}</pre>
<p>Transcript saved to: {{ filename }}</p>
{% endif %}
"""

@app.route("/", methods=["GET", "POST"])
def index():
    app.logger.debug("Index page accessed")
    summary = None
    filename = None
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        app.logger.debug(f"POST request received with URL: {url}")
        video_id = extract_video_id(url)
        app.logger.debug(f"Extracted video ID: {video_id}")
        if video_id:
            video_title = get_video_title(video_id)
            app.logger.debug(f"Video title: {video_title}")
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
                app.logger.debug(f"Transcript saved to: {filename}")
            else:
                app.logger.warning("Transcript not fetched")
        else:
            app.logger.warning("Invalid video ID extracted")
    return render_template_string(HTML_TEMPLATE, summary=summary, filename=filename)

if __name__ == "__main__":
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port)