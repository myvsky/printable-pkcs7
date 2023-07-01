from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from cryptography.hazmat.primitives.serialization.pkcs7 import load_der_pkcs7_certificates
from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

from reportlab.platypus import SimpleDocTemplate, Paragraph, Frame
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Font
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# PDF handlers
from pdfrw import PdfReader, PdfWriter, PageMerge
from io import BytesIO

import locale


locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
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
async def upload(
    pkcs7_file: UploadFile = File(...), doc_file: UploadFile = File(...)):

    doc = await doc_file.read()
    pkcs7 = await pkcs7_file.read()

    data = parse_signature(
        load_der_pkcs7_certificates(pkcs7)[0]
    )

    wm = watermark(doc, data)

    merge(doc, wm)

    return {"redirect": "/download"}


@app.get("/download")
async def download():
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
    signed = cert.not_valid_before
    # Issuer
    gn = cert.subject.get_attributes_for_oid(NameOID.GIVEN_NAME)[0].value
    sur = cert.subject.get_attributes_for_oid(NameOID.SURNAME)[0].value
    bus = cert.subject.get_attributes_for_oid(NameOID.TITLE)[0].value

    return [
        f"Документ подписан электронной подписью {signed.strftime('%d %B %Y')}",
        f"{cn}",
        f"{bus} {sur} {gn}",
        f"Действителен до {valid.strftime('%d %B %Y')}",
        f"Сертификат {sn_hex}"
    ]


def watermark(doc, data) -> None:
    doc = PdfReader(fdata=doc)
    buf = BytesIO()

    w = float(doc.pages[-1].MediaBox[2])
    h = float(doc.pages[-1].MediaBox[3])

    pdf = Canvas(buf, pagesize=(w, h))
    frame = Frame(10, 10, w-20, 75, showBoundary=1)

    # Font setting
    pdfmetrics.registerFont(TTFont("CustomFont", "Mulish-ExtraBold.ttf"))
    custom_style = ParagraphStyle(name="CustomStyle", fontName="CustomFont", fontSize=7, textColor='blue')

    # Adding unique text from data to watermark
    content = [Paragraph(line, custom_style) for line in data]

    # Color handling
    pdf.setFillColorRGB(0, 0, 128)
    pdf.setStrokeColorRGB(0, 0, 128)

    frame.addFromList(content, pdf)
    pdf.save()

    return buf.getvalue()


def merge(doc, wm):
    new = PdfReader(fdata=wm)
    old = PdfReader(fdata=doc)

    out = PdfWriter()

    page = old.pages[-1]
    mb = page.MediaBox

    merger = PageMerge(page)
    merger.add(new.pages[0])
    merger.render()

    out_stream = BytesIO()

    out.addpages(old.pages)
    out.write(out_stream)

    global pdf_data
    pdf_data = out_stream.getvalue()