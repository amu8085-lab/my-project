import os, requests, json
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, CompositeVideoClip, TextClip, concatenate_videoclips, vfx, afx

audio_url = os.environ.get('AUDIO_URL')
chat_id = os.environ.get('CHAT_ID')
webhook_url = os.environ.get('WEBHOOK_URL')
pexels_key = os.environ.get('PEXELS_API_KEY')
scenes_data = json.loads(os.environ.get('SCENES_DATA', '[]'))

print(f"Total Scenes to render: {len(scenes_data)}")

# 1. Download Voiceover
with open("voiceover.mp3", "wb") as f:
    f.write(requests.get(audio_url).content)
voiceover = AudioFileClip("voiceover.mp3")

# Calculate duration per scene based on text length
total_chars = sum(len(s['text']) for s in scenes_data)

video_clips = []
headers = {"Authorization": pexels_key}

# 2. Process Each Scene (Download -> Cut -> Add Subtitle)
for i, scene in enumerate(scenes_data):
    keyword = scene.get('keyword', 'nature')
    text_line = scene.get('text', '')
    
    # Calculate how long this video clip should be
    scene_duration = voiceover.duration * (len(text_line) / total_chars)
    if scene_duration < 1.0: scene_duration = 1.0
    
    try:
        res = requests.get(f"https://api.pexels.com/videos/search?query={keyword}&per_page=1&orientation=portrait", headers=headers).json()
        video_url = res['videos'][0]['video_files'][0]['link']
        
        vid_path = f"vid_{i}.mp4"
        with open(vid_path, "wb") as f:
            f.write(requests.get(video_url).content)
            
        # Format Video
        clip = VideoFileClip(vid_path).subclip(0, scene_duration)
        clip = clip.resize(height=1920, width=1080)
        
        # Create Viral Subtitle Text
        txt_clip = TextClip(text_line, fontsize=70, color='white', font='DejaVu-Sans-Bold', stroke_color='black', stroke_width=3, method='caption', size=(900, None))
        txt_clip = txt_clip.set_position(('center', 'center')).set_duration(scene_duration)
        
        # Combine Video + Subtitle
        final_scene = CompositeVideoClip([clip, txt_clip])
        if i > 0: final_scene = final_scene.crossfadein(0.5)
            
        video_clips.append(final_scene)
        print(f"Scene {i+1} Ready: {keyword}")
    except Exception as e:
        print(f"Error on scene {i}: {e}")

# 3. Stitch Everything Together
final_video = concatenate_videoclips(video_clips, padding=-0.5, method="compose")

# 4. Add Background Music (BGM)
try:
    bgm = AudioFileClip("bgm.mp3").volumex(0.08)
    if bgm.duration < voiceover.duration:
        bgm = afx.audio_loop(bgm, duration=voiceover.duration)
    else:
        bgm = bgm.subclip(0, voiceover.duration)
    final_audio = CompositeAudioClip([voiceover, bgm])
except:
    final_audio = voiceover

final_video = final_video.set_audio(final_audio)

# 5. Render & Upload
print("Rendering Final VIRAL Video...")
final_video.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac")

try:
    files = {'reqtype': (None, 'fileupload'), 'fileToUpload': open('final_video.mp4', 'rb')}
    video_link = requests.post("https://catbox.moe/user/api.php", files=files).text.strip()
except:
    video_link = "Upload Failed"

# 6. Notify Telegram via N8N
payload = {"chat_id": chat_id, "message": "🔥 Bhai! VIRAL Video Ready hai (With Subtitles)! 🔥", "youtube_url": video_link}
try:
    requests.post(webhook_url, json=payload, timeout=15)
except Exception as e:
    print(f"N8N warning: {e}")
