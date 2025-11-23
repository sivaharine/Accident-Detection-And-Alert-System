🚨 Accident Detection & Alert System — AI + FastAPI + Gemini Vision

This project is an AI-powered traffic accident monitoring and emergency alert system built using FastAPI, Gemini 2.5 Flash Vision, OpenCV, MongoDB, and Twilio. It automatically detects accidents from uploaded CCTV/road surveillance videos, identifies vehicle type, stores incident data, and sends real-time SMS alerts.

✅ Key Features

🎥 Upload any CCTV/road surveillance video

🤖 Gemini Vision detects accidents frame-by-frame

🚗 Classifies vehicle type (car, bike, truck, bus, etc.)

🗂️ Saves accident image, video clip & timestamp in MongoDB

📩 Sends SMS alerts via Twilio to emergency contacts

📊 API endpoints to fetch videos, images & analytics

🛡 Built-in CORS, input validation & secure backend structure

🛠️ Tech Stack

Backend: FastAPI, Python

AI Model: Gemini 2.5 Flash (Vision)

Video Processing: OpenCV, PIL

Database: MongoDB

Alerts: Twilio SMS API

Other Tools: Base64 encoding, tempfile, deque frame buffer

📂 System Workflow

Video Upload → Extract Frames → Gemini Accident Detection → Vehicle Classification → Save Clip + Image → Store in MongoDB → Send SMS Alert → Provide API Response
