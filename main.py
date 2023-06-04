from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from cryptography.hazmat.primitives.serialization.pkcs7 import load_der_pkcs7_certificates
from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

from fpdf import FPDF
from pdfrw import PdfReader, PageMerge, PdfWriter
from io import BytesIO


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
    return StreamingResponse(BytesIO(pdf_data),
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
    stamp.add_page(format=(200, 75))

    stamp.add_font("Mulish", '', "Mulish-ExtraBold.ttf", uni=True)
    stamp.set_font('Mulish', '', size=8)

    # Filling pdf
    stamp.cell(h=5, txt= "Этот документ подписан электронной подписью", ln=1)
    for v in data:
        stamp.cell(h=5, txt=f'{v}', ln=1)

    return stamp.output(dest='S')


def merge_pdf(doc, stamp):
    # Basic definitions
    original_pdf = PdfReader(fdata=doc)
    stamp_pdf = PdfReader(BytesIO(stamp))
    last_page = PageMerge(original_pdf.pages[
        len(original_pdf.pages) - 1
    ])

    stamped_page = last_page.add(stamp_pdf.pages[0])

    # Calculating size of original document
    last_page_x, last_page_y, last_page_w, last_page_h = map(
    float, original_pdf.pages[len(original_pdf.pages) - 1].MediaBox)
    stamp_x, stamp_y, stamp_w, stamp_h = map(
        float, stamp_pdf.pages[0].MediaBox
    )
    # Merge original document and stamp
    stamped_page.x = last_page_w - stamp_w
    stamped_page.y = last_page_y - 100
    last_page.render()

    buffer_data = BytesIO()
    PdfWriter().write(buffer_data, original_pdf)
    global pdf_data
    pdf_data = buffer_data.getvalue()