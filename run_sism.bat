@echo off
echo Starting SISM Backend Server...
start cmd /k "cd C:\Users\AJAI\OneDrive\Documents\DSA\Anti-Gravity\SISM && .\venv\Scripts\activate && cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo Starting SISM Next.js Frontend...
start cmd /k "cd C:\Users\AJAI\OneDrive\Documents\DSA\Anti-Gravity\SISM\frontend && npm run dev"

echo SISM is starting!
echo Backend API available at: http://localhost:8000/docs
echo Frontend available at: http://localhost:3000
