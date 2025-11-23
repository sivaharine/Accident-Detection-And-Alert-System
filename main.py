from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
import os
import tempfile
import collections
import base64
import google.generativeai as genai
from PIL import Image
import numpy as np
from datetime import datetime
from pymongo import MongoClient
from typing import Optional
from twilio.rest import Client


# Initialize FastAPI app
app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# twilio config
account_sid = 'AC5dd51f5d26113ffbadbc906df1fc9dfd'
auth_token = '998c3bb6608b80663f6ab52d7510df5b'
twilio_number = '+14159652912'
destination_number = '+910000000000'

try:
    tClient = Client(account_sid, auth_token)
    # Test the client configuration
    account = tClient.api.accounts(account_sid).fetch()
    print(f"Twilio account configured successfully: {account.friendly_name}")
except Exception as init_error:
    print(f"Twilio initialization error: {init_error}")
    tClient = None
    
# Gemini setup
genai.configure(api_key="AIzaSyDjnWyRU4Q8_rgOC-Hnj6wPC9PWfy93kHA")
model = genai.GenerativeModel("gemini-2.5-flash")

# MongoDB setup
client = MongoClient("mongodb://localhost:27017")
db = client["accident_detection"]
accident_logs = db["logs"]

# Globals
frame_buffer = collections.deque(maxlen=120)
accident_frame = None
VALID_VEHICLE_TYPES = ["car", "truck", "bus", "bike", "auto", "other"]

def extract_frames(video_path, frame_interval=240):
    cap = cv2.VideoCapture(video_path)
    frames = []
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_buffer.append(frame)
        if frame_count % frame_interval == 0:
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            frames.append((pil_img, frame))

        frame_count += 1

    cap.release()
    return frames

def save_video(frames, output_path, fps=30):
    if not frames:
        return None

    height, width, _ = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 (better browser support)

    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    for frame in frames:
        out.write(frame)
    out.release()

    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return output_path
    return None

def frame_to_base64(frame):
    _, buffer = cv2.imencode('.jpg', frame)
    return base64.b64encode(buffer).decode('utf-8')

def analyze_frame_with_gemini(image: Image) -> str:
    try:
        prompt = "Is there an accident? Reply True or False."
        response = model.generate_content([image, prompt])
        return response.text.strip().lower()
    except Exception as e:
        print("Gemini error:", e)
        return "false"

def detect_vehicle_type(image: Image) -> str:
    try:
        prompt = "What type of vehicle is in this accident? Choose one: car, truck, bus, bike, auto, or other."
        response = model.generate_content([image, prompt])
        text = response.text.lower()
        for t in VALID_VEHICLE_TYPES:
            if t in text:
                return t
        return "other"
    except Exception as e:
        print("Gemini vehicle type error:", e)
        return "other"

@app.post("/upload/")
async def upload_video(file: UploadFile = File(...), vehicle_type: Optional[str] = Form(None)):
    frame_buffer.clear()
    global accident_frame
    accident_frame = None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
        temp_video.write(await file.read())
        video_path = temp_video.name

    try:
        frames = extract_frames(video_path)
        os.remove(video_path)

        for pil_frame, cv_frame in frames:
            result = analyze_frame_with_gemini(pil_frame)
            if "true" in result:
                accident_frame = cv_frame

                if not vehicle_type or vehicle_type not in VALID_VEHICLE_TYPES:
                    vehicle_type = detect_vehicle_type(pil_frame)
                else:
                    vehicle_type = vehicle_type.lower()

                os.makedirs("videos", exist_ok=True)
                os.makedirs("images", exist_ok=True)

                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

                video_filename = f"accident_clip_{timestamp_str}.mp4"
                image_filename = f"accident_frame_{timestamp_str}.jpg"
                video_output_path = os.path.join("videos", video_filename)
                image_output_path = os.path.join("images", image_filename)

                saved_path = save_video(list(frame_buffer), video_output_path)
                if not saved_path:
                    return {"error": "Video saving failed. Possibly due to codec issue."}

                cv2.imwrite(image_output_path, accident_frame)

                accident_logs.insert_one({
                    "timestamp": datetime.now(),
                    "video_path": video_output_path,
                    "image_path": image_output_path,
                    "vehicle_type": vehicle_type
                })
                try:
                    if tClient is None:
                        print("Twilio client not initialized")
                        raise Exception("Twilio client not available")
                    
                    sms_body = f"🚨 Accident detected!\nVehicle Type: {vehicle_type.capitalize()}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    message = tClient.messages.create(
                        body=sms_body,
                        from_=twilio_number,
                        to=destination_number
                    )
                    print(f"SMS sent successfully. Message SID: {message.sid}")
                    print(f"SMS Status: {message.status}")
                    
                except Exception as sms_error:
                    print(f"SMS sending failed: {sms_error}")
                    # Log the specific error details
                    if hasattr(sms_error, 'code'):
                        print(f"Twilio Error Code: {sms_error.code}")
                    if hasattr(sms_error, 'msg'):
                        print(f"Twilio Error Message: {sms_error.msg}")
                return {
                    "accident_detected": True,
                    "video_path": f"/accident_video/{video_filename}",
                    "frame_path": f"/accident_frame/{image_filename}",
                    "frame_base64": frame_to_base64(accident_frame),
                    "vehicle_type": vehicle_type
                }

        return {"accident_detected": False}

    except Exception as e:
        return {"error": str(e)}

@app.post("/report_accident/")
async def report_accident(vehicle_type: str = Form(...), file: UploadFile = File(...)):
    if vehicle_type.lower() not in VALID_VEHICLE_TYPES:
        return {"error": f"Invalid vehicle type. Valid types: {', '.join(VALID_VEHICLE_TYPES)}"}
    return await upload_video(file=file, vehicle_type=vehicle_type)

@app.get("/accident_video/{filename}")
async def get_video(filename: str):
    file_path = os.path.join("videos", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4")
    return {"error": "Video not found"}

@app.get("/accident_frame/{filename}")
async def get_frame(filename: str):
    file_path = os.path.join("images", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/jpeg")
    return {"error": "Image not found"}

@app.get("/accident_images/")
async def get_all_accident_images():
    try:
        records = accident_logs.find({}, {"_id": 0, "timestamp": 1, "image_path": 1, "vehicle_type": 1})
        results = [{
            "timestamp": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "image_path": f"/accident_frame/{os.path.basename(r['image_path'])}",
            "vehicle_type": r["vehicle_type"]
        } for r in records]
        return {"images": results}
    except Exception as e:
        return {"error": str(e)}

@app.get("/accident_videos/")
async def get_all_accident_videos():
    try:
        records = accident_logs.find({}, {"_id": 0, "timestamp": 1, "video_path": 1, "image_path": 1, "vehicle_type": 1})
        results = [{
            "timestamp": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "video_path": f"/accident_video/{os.path.basename(r['video_path'])}",
            "image_path": f"/accident_frame/{os.path.basename(r['image_path'])}",
            "vehicle_type": r["vehicle_type"]
        } for r in records]
        return {"videos": results}
    except Exception as e:
        return {"error": str(e)}

@app.get("/vehicle_types/")
async def get_vehicle_types():
    try:
        pipeline = [
            {"$group": {"_id": "$vehicle_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        results = list(accident_logs.aggregate(pipeline))
        return {"vehicle_stats": [{"vehicle_type": r["_id"], "count": r["count"]} for r in results]}
    except Exception as e:
        return {"error": str(e)}
