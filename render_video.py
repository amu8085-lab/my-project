import os, requests, json, subprocess
import moviepy.editor as mpe
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, CompositeVideoClip, TextClip, concatenate_videoclips, vfx, afx, ImageClip, ColorClip

full_text = os.environ.get('FULL_TEXT', 'Ek baar ki baat hai.')
chat_id = os.environ.get('CHAT_ID')
webhook_url = os.environ.get('WEBHOOK_URL')
pexels_key = os.environ.get('PEXELS_API_KEY')
scenes_data = json.loads(os.environ.get('SCENES_DATA', '[]'))

print(f"Total Scenes to render: {len(scenes_data)}")

# 1. FREE Premium Voiceover (Hindi Male Voice)
print("Generating FREE AI Voiceover using Edge TTS...")
subprocess.run(['edge-tts', '--voice', 'hi-IN-MadhurNeural', '--text', full_text, '--write-media', 'voiceover.mp3'])

voiceover = AudioFileClip("voiceover.mp3")
total_chars = sum(len(s['text']) for s in scenes_data)
video_clips = []
audio_clips = [voiceover]
headers = {"Authorization": pexels_key}
current_time = 0.0

# Sound Effects Files Load karna (SFX)
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
    
    scene_duration = voiceover.duration * (len(text_line) / max(total_chars, 1))
    if scene_duration < 1.0: scene_duration = 1.0
    
    try:
        res = requests.get(f"https://api.pexels.com/videos/search?query={keyword}&per_page=1&orientation=portrait", headers=headers).json()
        video_url = res['videos'][0]['video_files'][0]['link']
        
        vid_path = f"vid_{i}.mp4"
        with open(vid_path, "wb") as f:
            f.write(requests.get(video_url).content)
            
        clip = VideoFileClip(vid_path).subclip(0, scene_duration).resize(height=1920, width=1080)
        
        # --- NEW BOLDER TEXT RENDERING (FOR 100% VISIBILITY) ---
        # 1. Create the TextClip (DejaVu Sans Bold humesha install hoti hai free server pe)
        txt_clip = TextClip(text_line, fontsize=80, color='yellow', font='DejaVu-Sans-Bold', stroke_color='black', stroke_width=5, method='caption', size=(900, None))
        
        # 2. Create a background rectangle box to guarantee readability
        text_w, text_h = txt_clip.size
        # Thoda padding add karo box mein
        box_w, box_h = text_w + 100, text_h + 100
        bg_clip = ColorClip(size=(box_w, box_h), color=(0,0,0)).set_opacity(0.6) # 60% translucent black
        
        # 3. Combine Text + Box to form a caption block
        txt_composite = CompositeVideoClip([bg_clip.set_position(('center', 'center')), txt_clip.set_position(('center', 'center'))]).set_duration(scene_duration).set_position(('center', 0.65)) # Centered horizontally, 65% down
        
        # 4. Composite onto Video clip (Adding start delay for "Pop" effect)
        final_scene = CompositeVideoClip([clip, txt_composite.set_start(0.2)]).set_duration(scene_duration)
        
        if i > 0:
            final_scene = final_scene.crossfadein(0.3)
            
        video_clips.append(final_scene)
        
        if whoosh_sfx:
            audio_clips.append(whoosh_sfx.set_start(current_time))
        if pop_sfx:
            audio_clips.append(pop_sfx.set_start(current_time + 0.2))
            
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

final_audio = CompositeAudioClip(audio_clips)
final_video = final_video.set_audio(final_audio)

# 5. Render & Upload (Safe Upload Method)
print("Rendering Final ZERO-COST VIRAL Video...")
final_video.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac", threads=2)

try:
    files = {'reqtype': (None, 'fileupload'), 'fileToUpload': open('final_video.mp4', 'rb')}
    upload_res = requests.post("https://catbox.moe/user/api.php", files=files)
    video_link = upload_res.text.strip()
    if not video_link.startswith("http"):
        print(f"Catbox API Error: {video_link}")
        video_link = "Upload Failed"
except Exception as e:
    video_link = f"Upload Error: {e}"

# 6. Notify Telegram
print(f"🔥 FINAL YOUTUBE LINK: {video_link} 🔥")
payload = {"chat_id": chat_id, "message": "💰 Bhai! Tumhari ZERO-COST VIRAL AI Video (With Fixed Subtitles) Ready hai!", "youtube_url": video_link}
try:
    requests.post(webhook_url, json=payload, timeout=15)
except Exception as e:
    print(f"N8N warning: {e}")
