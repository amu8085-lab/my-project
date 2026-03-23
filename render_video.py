import os, requests, json, subprocess
import moviepy.editor as mpe
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, CompositeVideoClip, TextClip, concatenate_videoclips, vfx, afx, ImageClip, ColorClip

HINDI_FONT_FILE = "Hindi.ttf" 

full_text = os.environ.get('FULL_TEXT', 'Ek baar ki baat hai.')
chat_id = os.environ.get('CHAT_ID')
webhook_url = os.environ.get('WEBHOOK_URL')
pexels_key = os.environ.get('PEXELS_API_KEY')
scenes_data = json.loads(os.environ.get('SCENES_DATA', '[]'))

print(f"Total Scenes to render: {len(scenes_data)}")

# 1. FREE AI Voiceover
subprocess.run(['edge-tts', '--voice', 'hi-IN-MadhurNeural', '--text', full_text, '--write-media', 'voiceover.mp3'])
voiceover = AudioFileClip("voiceover.mp3")

total_chars = sum(len(s['text']) for s in scenes_data)
video_clips = []
audio_clips = [voiceover]
headers = {"Authorization": pexels_key}
current_time = 0.0

try:
    whoosh_sfx = AudioFileClip("whoosh.mp3").volumex(0.8)
    pop_sfx = AudioFileClip("pop.mp3").volumex(1.0)
except:
    whoosh_sfx = pop_sfx = None

viral_colors = ['#FFD400', '#00FFFF', '#FFFFFF', '#39FF14'] 

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
            
        # THE FIX: STRICT CANVAS LOCK AND CENTER ZOOM
        clip = VideoFileClip(vid_path).subclip(0, scene_duration)
        clip = clip.resize(height=1920)
        
        # Zoom apply kiya aur usko forcefully Center mein lock kar diya
        zoomed_clip = clip.resize(lambda t: 1.0 + 0.05 * (t / scene_duration)).set_position(('center', 'center'))
        
        # Dark overlay ko bhi center lock kiya
        dark_overlay = ColorClip(size=(1080, 1920), color=(0,0,0)).set_opacity(0.35).set_position(('center', 'center')).set_duration(scene_duration)
        
        words = text_line.split(' ')
        chunk_size = 3 
        chunks = [' '.join(words[j:j + chunk_size]) for j in range(0, len(words), chunk_size)]
        
        word_clips = []
        duration_per_chunk = scene_duration / len(chunks)
        
        for w_i, chunk in enumerate(chunks):
            current_color = viral_colors[w_i % len(viral_colors)]
            
            # Thoda font size 110 kiya taaki fit aaram se aaye
            main_txt = TextClip(chunk, fontsize=110, color=current_color, font=HINDI_FONT_FILE, stroke_color='black', stroke_width=7, method='caption', size=(950, None))
            txt_pos = main_txt.set_position(('center', 'center')).set_duration(duration_per_chunk).set_start(w_i * duration_per_chunk)
            word_clips.append(txt_pos)
        
        # --- THE CRITICAL FIX: Add `size=(1080, 1920)` to force strict YouTube Shorts frame ---
        final_scene = CompositeVideoClip([zoomed_clip, dark_overlay] + word_clips, size=(1080, 1920)).set_duration(scene_duration)
        
        if i > 0: final_scene = final_scene.crossfadein(0.3)
            
        video_clips.append(final_scene)
        
        if whoosh_sfx: audio_clips.append(whoosh_sfx.set_start(current_time))
        if pop_sfx:
            for w_i in range(len(chunks)):
                audio_clips.append(pop_sfx.set_start(current_time + (w_i * duration_per_chunk)))
                
        current_time += scene_duration
        print(f"Scene {i+1} Ready: {keyword}")
    except Exception as e:
        print(f"Error on scene {i}: {e}")

# Stitch Everything
final_video = concatenate_videoclips(video_clips, padding=-0.3, method="compose")

# Add BGM
try:
    bgm = AudioFileClip("bgm.mp3").volumex(0.08)
    if bgm.duration < final_video.duration: bgm = afx.audio_loop(bgm, duration=final_video.duration)
    else: bgm = bgm.subclip(0, final_video.duration)
    audio_clips.append(bgm)
except: pass

final_audio = CompositeAudioClip(audio_clips)
final_video = final_video.set_audio(final_audio)

# Render & upload
print("Rendering Final GOD-TIER VIRAL Video...")
final_video.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac", threads=2)

try:
    files = {'reqtype': (None, 'fileupload'), 'fileToUpload': open('final_video.mp4', 'rb')}
    video_link = requests.post("https://catbox.moe/user/api.php", files=files).text.strip()
except: video_link = "Upload Failed"

# Notify Telegram
print(f"🔥 FINAL YOUTUBE LINK: {video_link} 🔥")
payload = {"chat_id": chat_id, "message": "👑 Bhai! The PERFECT 1000/10 Video Ready! (Fixed Center Canvas) 🔥", "youtube_url": video_link}

try:
    requests.post(webhook_url, json=payload, timeout=15)
except Exception as e:
    print(f"Warning: N8N unreachable. Error: {e}")
