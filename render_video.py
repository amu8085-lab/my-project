import os, requests
from moviepy.editor import VideoFileClip, AudioFileClip, vfx

# 1. N8N se aaye hue variables lena
audio_url = os.environ.get('AUDIO_URL')
keyword = os.environ.get('SEARCH_KEYWORD')
chat_id = os.environ.get('CHAT_ID')
webhook_url = os.environ.get('WEBHOOK_URL')
pexels_key = os.environ.get('PEXELS_API_KEY')

print(f"Keyword received: {keyword}")

# 2. WordPress se Audio Download karna
print("Downloading Audio...")
audio_data = requests.get(audio_url).content
with open("audio.mp3", "wb") as f:
    f.write(audio_data)

# 3. Pexels se Background Video Download karna
print("Searching Pexels for video...")
headers = {"Authorization": pexels_key}
res = requests.get(f"https://api.pexels.com/videos/search?query={keyword}&per_page=1", headers=headers).json()
video_url = res['videos'][0]['video_files'][0]['link']

print("Downloading Background Video...")
video_data = requests.get(video_url).content
with open("bg_video.mp4", "wb") as f:
    f.write(video_data)

# 4. Audio aur Video ko Merge karna (MoviePy)
print("Rendering Video...")
audio_clip = AudioFileClip("audio.mp3")
video_clip = VideoFileClip("bg_video.mp4")

# Agar video chota hai toh usko audio ke barabar loop karna
if video_clip.duration < audio_clip.duration:
    video_clip = video_clip.fx(vfx.loop, duration=audio_clip.duration)
else:
    video_clip = video_clip.subclip(0, audio_clip.duration)

final_video = video_clip.set_audio(audio_clip)
final_video.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac")

# 5. Temporary server par upload karna (Test ke liye)
print("Uploading final video...")
try:
    files = {'file': open('final_video.mp4', 'rb')}
    upload_res = requests.post("https://file.io/?expires=1w", files=files).json()
    video_link = upload_res.get('link', 'File.io Error')
except Exception as e:
    print(f"Upload error: {e}")
    video_link = "Upload Server Down"

# 6. N8N Webhook ko Success Message bhejna
print("Pinging N8N...")
payload = {
    "chat_id": chat_id,
    "message": "🎉 Bhai! Tumhari video successfully render ho gayi hai!",
    "youtube_url": video_link
}
requests.post(webhook_url, json=payload)
print("Done!")
