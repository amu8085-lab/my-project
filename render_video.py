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
TARGET_W, TARGET_H = 1080, 1920

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
            
        # --- THE 2000/10 FIX: BULLETPROOF CROP & SCALE ---
        clip = VideoFileClip(vid_path).subclip(0, scene_duration)
        
        # Force height to 1920
        clip = clip.resize(height=TARGET_H)
        # Force width if it's too narrow
        if clip.w < TARGET_W:
            clip = clip.resize(width=TARGET_W)
        # PERFECT Center Crop
        clip = clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=TARGET_W, height=TARGET_H)
        
        # Smooth Ken Burns Zoom
        zoomed_clip = clip.resize(lambda t: 1.0 + 0.04 * (t / scene_duration)).set_position(('center', 'center'))
        
        # Premium Dark Overlay
        dark_overlay = ColorClip(size=(TARGET_W, TARGET_H), color=(0,0,0)).set_opacity(0.3).set_position(('center', 'center')).set_duration(scene_duration)
        
        words = text_line.split(' ')
        # 2000/10 PACING: Strictly 2 words per pop
        chunk_size = 2 
        chunks = [' '.join(words[j:j + chunk_size]) for j in range(0, len(words), chunk_size)]
        
        word_clips = []
        duration_per_chunk = scene_duration / len(chunks)
        
        for w_i, chunk in enumerate(chunks):
            current_color = viral_colors[w_i % len(viral_colors)]
            
            # --- THE 3D SHADOW EFFECT ---
            # Pehle ek kaala (black) text banaya aur thoda neeche/right shift kiya
            shadow_txt = TextClip(chunk, fontsize=130, color='black', font=HINDI_FONT_FILE, method='caption', size=(950, None))
            shadow_txt = shadow_txt.set_position(('center', 'center')).margin(top=10, left=10, opacity=0).set_duration(duration_per_chunk).set_start(w_i * duration_per_chunk)
            
            # Fir main coloured text uske theek upar rakha
            main_txt = TextClip(chunk, fontsize=130, color=current_color, font=HINDI_FONT_FILE, stroke_color='black', stroke_width=6, method='caption', size=(950, None))
            txt_pos = main_txt.set_position(('center', 'center')).set_duration(duration_per_chunk).set_start(w_i * duration_per_chunk)
            
            # Dono ko merge kar diya
            word_clips.extend([shadow_txt, txt_pos])
        
        # Strict Canvas Lock
        final_scene = CompositeVideoClip([zoomed_clip, dark_overlay] + word_clips, size=(TARGET_W, TARGET_H)).set_duration(scene_duration)
        
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
print("Rendering Final 2000/10 VIRAL Video...")
final_video.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac", threads=2)

try:
    files = {'reqtype': (None, 'fileupload'), 'fileToUpload': open('final_video.mp4', 'rb')}
    video_link = requests.post("https://catbox.moe/user/api.php", files=files).text.strip()
except: video_link = "Upload Failed"

# Notify Telegram
print(f"🔥 FINAL YOUTUBE LINK: {video_link} 🔥")
payload = {"chat_id": chat_id, "message": "👑 Bhai! The 2000/10 GOD TIER Video Ready! (Massive Text + 3D Shadows + Perfect Crop) 🔥", "youtube_url": video_link}

try:
    requests.post(webhook_url, json=payload, timeout=15)
except Exception as e:
    print(f"Warning: N8N unreachable. Error: {e}")
