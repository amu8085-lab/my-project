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

total_chars = sum(len(s['text']) for s in scenes_data)
video_clips = []

# Audio array mein pehle se voiceover daal diya
audio_clips = [voiceover] 
headers = {"Authorization": pexels_key}

current_time = 0.0 # Time track karne ke liye (SFX ke liye zaroori hai)

# SFX Files Load karna (Agar upload ki hongi toh bajengi)
try:
    whoosh_sfx = AudioFileClip("whoosh.mp3").volumex(0.7)
except:
    whoosh_sfx = None

try:
    pop_sfx = AudioFileClip("pop.mp3").volumex(0.9)
except:
    pop_sfx = None

# 2. Process Each Scene
for i, scene in enumerate(scenes_data):
    keyword = scene.get('keyword', 'nature')
    text_line = scene.get('text', '')
    
    # Scene ka time calculate karna
    scene_duration = voiceover.duration * (len(text_line) / total_chars)
    if scene_duration < 1.0: scene_duration = 1.0
    
    try:
        res = requests.get(f"https://api.pexels.com/videos/search?query={keyword}&per_page=1&orientation=portrait", headers=headers).json()
        video_url = res['videos'][0]['video_files'][0]['link']
        
        vid_path = f"vid_{i}.mp4"
        with open(vid_path, "wb") as f:
            f.write(requests.get(video_url).content)
            
        # Video Format
        clip = VideoFileClip(vid_path).subclip(0, scene_duration)
        clip = clip.resize(height=1920, width=1080)
        
        # Viral Subtitle (Bright Yellow with bold stroke)
        txt_clip = TextClip(text_line, fontsize=75, color='yellow', font='DejaVu-Sans-Bold', stroke_color='black', stroke_width=4, method='caption', size=(950, None))
        
        # POP-UP EFFECT: Text video aane ke 0.2 seconds baad aayega
        txt_clip = txt_clip.set_position(('center', 'center')).set_start(0.2).set_duration(scene_duration - 0.2)
        
        final_scene = CompositeVideoClip([clip, txt_clip]).set_duration(scene_duration)
        if i > 0: 
            final_scene = final_scene.crossfadein(0.3) # Smooth cut
            
        video_clips.append(final_scene)
        
        # --- AUDIO SFX MIXING TIMELINE ---
        if whoosh_sfx:
            audio_clips.append(whoosh_sfx.set_start(current_time)) # Scene aate hi Whoosh
        if pop_sfx:
            audio_clips.append(pop_sfx.set_start(current_time + 0.2)) # 0.2s baad Pop jab text aaye
            
        current_time += scene_duration
        print(f"Scene {i+1} Ready: {keyword}")
    except Exception as e:
        print(f"Error on scene {i}: {e}")

# 3. Stitch Everything Together
final_video = concatenate_videoclips(video_clips, padding=-0.3, method="compose")

# 4. Add Background Music (BGM)
try:
    bgm = AudioFileClip("bgm.mp3").volumex(0.08)
    if bgm.duration < final_video.duration:
        bgm = afx.audio_loop(bgm, duration=final_video.duration)
    else:
        bgm = bgm.subclip(0, final_video.duration)
    audio_clips.append(bgm)
except:
    pass

# Combine Voice + BGM + Whooshes + Pops into one masterpiece track
final_audio = CompositeAudioClip(audio_clips)
final_video = final_video.set_audio(final_audio)

# 5. Render & Upload (Using 2 threads to prevent Github crash)
print("Rendering Final 100/10 VIRAL Video...")
final_video.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac", threads=2)

try:
    files = {'reqtype': (None, 'fileupload'), 'fileToUpload': open('final_video.mp4', 'rb')}
    video_link = requests.post("https://catbox.moe/user/api.php", files=files).text.strip()
except:
    video_link = "Upload Failed"

# 6. Notify Telegram via N8N
print(f"🔥 FINAL YOUTUBE LINK: {video_link} 🔥")
payload = {"chat_id": chat_id, "message": "🚀 Bhai! Tumhari 100/10 Viral Video (With SFX) Ready hai!", "youtube_url": video_link}
try:
    requests.post(webhook_url, json=payload, timeout=15)
except Exception as e:
    print(f"N8N warning: {e}")
