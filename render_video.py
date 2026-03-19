import os, requests
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips, vfx

# 1. N8N se aaye variables
audio_url = os.environ.get('AUDIO_URL')
chat_id = os.environ.get('CHAT_ID')
webhook_url = os.environ.get('WEBHOOK_URL')
pexels_key = os.environ.get('PEXELS_API_KEY')

# Ab 3 scenes ke keywords aayenge
keywords = [
    os.environ.get('SCENE_1', 'nature'),
    os.environ.get('SCENE_2', 'city view'),
    os.environ.get('SCENE_3', 'night sky')
]

print(f"Keywords received: {keywords}")

# 2. Voiceover Download karna
print("Downloading Voiceover...")
with open("voiceover.mp3", "wb") as f:
    f.write(requests.get(audio_url).content)

voiceover = AudioFileClip("voiceover.mp3")
clip_duration = voiceover.duration / 3 # Har video kitni der chalegi

# 3. Pexels se 3 Videos Download aur Process karna
print("Downloading and processing videos from Pexels...")
headers = {"Authorization": pexels_key}
video_clips = []

for i, kw in enumerate(keywords):
    try:
        res = requests.get(f"https://api.pexels.com/videos/search?query={kw}&per_page=1&orientation=portrait", headers=headers).json()
        video_url = res['videos'][0]['video_files'][0]['link']
        
        vid_path = f"vid_{i}.mp4"
        with open(vid_path, "wb") as f:
            f.write(requests.get(video_url).content)
            
        # Video ko sahi size aur time ka banana
        clip = VideoFileClip(vid_path).subclip(0, clip_duration)
        clip = clip.resize(height=1920, width=1080) # YouTube Shorts size
        
        # Pehle clip ko chhodkar baki me crossfade effect dalna
        if i > 0:
            clip = clip.crossfadein(1.0) 
            
        video_clips.append(clip)
    except Exception as e:
        print(f"Error fetching video for {kw}: {e}")

# 4. Videos ko Jodna (Stitching)
print("Stitching videos with effects...")
final_video = concatenate_videoclips(video_clips, padding=-1.0, method="compose")

# 5. Background Music (BGM) Mix karna
# Note: Repo me 'bgm.mp3' naam ki ek file pehle se honi chahiye!
try:
    bgm = AudioFileClip("bgm.mp3").fx(vfx.volumex, 0.1) # BGM volume 10%
    if bgm.duration < voiceover.duration:
        bgm = bgm.fx(vfx.loop, duration=voiceover.duration)
    else:
        bgm = bgm.subclip(0, voiceover.duration)
        
    final_audio = CompositeAudioClip([voiceover, bgm])
except:
    print("bgm.mp3 not found, using only voiceover.")
    final_audio = voiceover

final_video = final_video.set_audio(final_audio)

# Render karna
print("Rendering Final Pro Video...")
final_video.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac")

# 6. Catbox par upload karna
print("Uploading final video to Catbox...")
try:
    files = {'reqtype': (None, 'fileupload'), 'fileToUpload': open('final_video.mp4', 'rb')}
    upload_res = requests.post("https://catbox.moe/user/api.php", files=files)
    video_link = upload_res.text.strip()
except Exception as e:
    video_link = "Upload Failed"

# 7. N8N ko success bhejna
print("Pinging N8N...")
payload = {"chat_id": chat_id, "message": "🎬 Bhai! Tumhari PRO video ready hai!", "youtube_url": video_link}
requests.post(webhook_url, json=payload)
print("Done!")
