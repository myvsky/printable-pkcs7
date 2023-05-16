import logging
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
# Configure CORS
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("templates/index.html", "r") as file:
        html_content = file.read()
    logging.info("All done.")
    return HTMLResponse(content=html_content)

@app.post("/upload")
async def process_file(file: UploadFile = File(...)):
    logging.info(f"We wait")
    contents = await file.read()  

    file_path = os.path.join(os.getcwd(), file.filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    logging.info(f"File saved: {file_path}")
    return {"message": "File uploaded and processed successfully"}  