# Web app holding
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# SIG parsing
import subprocess
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

# Stamp creating
from PIL import Image, ImageDraw, ImageFont

# Configure CORS
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local servers for testing
        "http://localhost:8000", "http://127.0.0.1:8000",
        # Vercel app
        "https://printable-pkcs7.vercel.app/"
        ],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)

@app.post("/upload")
async def collect_upload(sig_file: UploadFile = File(...), pdf_file: UploadFile = File(...)):
    pdf = await pdf_file.read()
    sig = await sig_file.read()

    stamp_info = parse_sig(pdf, sig)
    create_stamp(stamp_info)
    return {"message": "Files uploaded and processed successfully"}


def parse_sig(pdf, sig) -> dict:

    # Specify the path to the input PKCS#7 certificate file
    input_file = 'Кузнецова договор.pdf (1).p7s'

    # Run the openssl command to convert the certificate and capture the output
    output = subprocess.run(['openssl', 'pkcs7', '-in', input_file, '-inform', 'DER', '-print_certs'], capture_output=True)

    # Extract the PEM certificate data from the output
    pem_data = output.stdout

    # Parse the PEM certificate data
    p7s = x509.load_pem_x509_certificate(pem_data, default_backend())

    cn = p7s.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    document_id = p7s.serial_number
    expiration_time = p7s.not_valid_after

    # Signature verification
    signature = p7s.signature
    try:
        p7s.public_key().verify(
            signature,
            data,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        print("Signature is valid.")
    except:
        print("Signature is invalid.")

    return {
        "Действительность документа:": signature,
        "Владелец документа:": cn,
        "Серийный номер документа": document_id,
        "Дата истечения действительности подписи": expiration_time
    }

def create_stamp(data):

    # Define stamp size and background color
    stamp_width = 400
    stamp_height = 200
    background_color = (255, 255, 255)  # White

    # Define font properties
    font_size = 16
    font_color = (20, 20, 150)  # Black
    font_path = 'Stencil.ttf'  # Replace with the path to your font file

    # Define border properties
    border_color = (20, 20, 150)  # Blue
    border_width = 5
    # border_radius = 10

    # Create a blank stamp image
    stamp_image = Image.new('RGB', (stamp_width, stamp_height), background_color)
    draw = ImageDraw.Draw(stamp_image)

    # Set the font
    font = ImageFont.truetype(font_path, font_size)

    # Calculate the vertical position for each object's information
    line_height = font.getsize('SAMPLE')[1]  # Adjust the sample text to fit your font
    vertical_position = 20  # Initial vertical position

    # Draw each object's information on the stamp image
    for key, value in data.items():
        # Format the information string
        info_str = f'{key}: {value}'

        # Draw the information text on the stamp image
        draw.text((20, vertical_position), info_str, font=font, fill=font_color)

        # Update the vertical position for the next object
        vertical_position += line_height

    # Create a border around the stamp image
    border_box = [(0, 0), (stamp_width - 1, stamp_height - 1)]
    draw.rectangle(border_box, outline=border_color, width=border_width)

    # Save the stamp image
    stamp_image.save('stamp.png')