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

# 1. FREE AI Voiceover (Madhur Hindi)
subprocess.run(['edge-tts', '--voice', 'hi-IN-MadhurNeural', '--text', full_text, '--write-media', 'voiceover.mp3'])
voiceover = AudioFileClip("voiceover.mp3")

total_chars = sum(len(s['text']) for s in scenes_data)
video_clips = []
audio_clips = [voiceover]
headers = {"Authorization": pexels_key}
current_time = 0.0

try:
    whoosh_sfx = AudioFileClip("whoosh.mp3").volumex(0.7)
    pop_sfx = AudioFileClip("pop.mp3").volumex(0.9)
except:
    whoosh_sfx = pop_sfx = None

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
        
        # Ken Burns Zoom
        clip = clip.resize(lambda t: 1.0 + 0.1 * (t / scene_duration))
        
        words = text_line.split(' ')
        chunk_size = 4 
        chunks = [' '.join(words[j:j + chunk_size]) for j in range(0, len(words), chunk_size)]
        
        word_clips = []
        duration_per_chunk = scene_duration / len(chunks)
        
        for w_i, chunk in enumerate(chunks):
            txt_clip = TextClip(chunk, fontsize=90, color='yellow', font=HINDI_FONT_FILE, stroke_color='black', stroke_width=5, method='caption', size=(950, None))
            highlight_txt = TextClip(chunk, fontsize=90, color='magenta', font=HINDI_FONT_FILE, method='caption', size=(950, None))
            
            # Yahan se vfx error wali line hata di gayi hai
            w_block = CompositeVideoClip([txt_clip, highlight_txt.set_duration(0.3).crossfadeout(0.2)])
            w_block = w_block.set_duration(duration_per_chunk).set_start(w_i * duration_per_chunk)
            
            word_clips.append(w_block)

        bg_clip = ColorClip(size=(1080, 250), color=(0,0,0)).set_opacity(0.6).set_duration(scene_duration).set_position(('center', 'center'))
        
        txt_composite = CompositeVideoClip([bg_clip] + word_clips).set_duration(scene_duration).set_position(('center', 0.60)) 
        
        final_scene = CompositeVideoClip([clip, txt_composite]).set_duration(scene_duration)
        if i > 0: final_scene = final_scene.crossfadein(0.3)
            
        video_clips.append(final_scene)
        
        if whoosh_sfx: audio_clips.append(whoosh_sfx.set_start(current_time))
        current_time += scene_duration
        print(f"Scene {i+1} Ready: {keyword}")
    except Exception as e:
        print(f"Error on scene {i}: {e}")

# Stitch
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
print("Rendering Final 500/10 VIRAL Video...")
final_video.write_videofile("final_video.mp4", fps=24, codec="libx264", audio_codec="aac", threads=2)

try:
    files = {'reqtype': (None, 'fileupload'), 'fileToUpload': open('final_video.mp4', 'rb')}
    video_link = requests.post("https://catbox.moe/user/api.php", files=files).text.strip()
except: video_link = "Upload Failed"

# Notify Telegram
print(f"🔥 FINAL YOUTUBE LINK: {video_link} 🔥")
payload = {"chat_id": chat_id, "message": "💰 Bhai! 500/10 VIRAL AI Video Ready hai (Dynamic Zoom + Highlighted Text)! 🔥", "youtube_url": video_link}

try:
    requests.post(webhook_url, json=payload, timeout=15)
    print("Success: Message sent to N8N!")
except Exception as e:
    print(f"Warning: N8N unreachable. Error: {e}")
