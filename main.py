from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

import ssl
from cryptography.hazmat.primitives.serialization.pkcs7 import load_der_pkcs7_certificates
from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

from fpdf import FPDF


# Configure CORS so the server could exchange data with user
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
    allow_headers=["*"]
)
pdf_data = None


# Rendering HTML page
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)


@app.post("/upload")
async def data_exchange(
    pkcs7_file: UploadFile = File(...), doc_file: UploadFile = File(...)):

    doc = await doc_file.read()
    pkcs7 = await pkcs7_file.read()

    data = parse_signature(
        load_der_pkcs7_certificates(pkcs7)[0]
    )

    stamp = create_stamp(doc, data)

    merge_pdf(doc, stamp)

    return {"redirect": "/download"}


@app.get("/download")
async def download_page():
    global pdf_data
    return StreamingResponse(pdf_data,
    media_type="application/pdf",
    headers={
        "Content-Disposition": "attachment; filename=output.pdf"
    })


def parse_signature(cert) -> list:
    # Serial number in integer value
    sn = cert.serial_number
    # Serial number in HEX
    sn_hex = hex(sn).upper().replace('0X', '')
    # Issuer's commmon name
    cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    # Valid until : datetime object
    valid = cert.not_valid_after

    return [
        cn,
        valid,
        f"Сертификат {sn_hex}"
    ]


# Returns stamped PDF
def create_stamp(doc, data):

    stamp = FPDF()
    stamp.add_page(format=(200, 100))

    stamp.add_font("Mulish", '', "Mulish-ExtraBold.ttf", uni=True)
    stamp.set_font('Mulish', '', size=8)

    # Filling pdf
    stamp.cell(150, 5, "Этот документ подписан электронной подписью", ln=1)
    for v in data:
        stamp.cell(150, 5, f'{v}', ln=1)

    stamp.output('out.pdf', 'F')


def merge_pdf(doc, stamp):
    # Calculating size of original document
    pdf = PdfReader(fdata=pdf)
    last_page_x, last_page_y, last_page_w, last_page_h = map(
    float, pdf.pages[len(pdf.pages) - 1].MediaBox)
    num_pages = len(pdf.pages)
    for i, page in enumerate(pdf.pages):
        merge = PageMerge(page)
        if i == len(stamp.pages) - 1:
            merge.add(stamp.pages[0])
        PdfWriter().addpage(merge.render())

    
    buffer_data = BytesIO()
    PdfWriter().write(buffer_data, pdf)
    global pdf_data
    pdf_data = buffer_data.getvalue()