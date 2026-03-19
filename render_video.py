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
