from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

import OpenSSL.crypto as crypto
from OpenSSL.crypto import _lib, _ffi, X509

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from io import BytesIO
from pdfrw import PdfReader, PdfWriter, PageMerge


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


# Exchange data with user
@app.post("/upload")
async def data_exchange(
    pkcs7_file: UploadFile = File(...), doc_file: UploadFile = File(...)):
    doc = await doc_file.read()
    pkcs7 = await pkcs7_file.read()

    data = parse_signature(pkcs7)
    stamp = create_stamp(data)
    print_stamp(stamp, doc)
    return {"redirect": "/download"}


def parse_signature(pkcs7) -> dict:
    p7 = crypto.load_pkcs7_data(crypto.FILETYPE_ASN1, pkcs7)
    cert = get_certificates(p7)[0]
    return {
        "Владелец": cert.get_subject().commonName,
        "Издатель": cert.get_issuer().commonName,
        "Серийный номер документа": cert.get_serial_number(),
        "Дата истечения действительности подписи (Г-М-Д Ч:М:С)": 
        datetime.strptime(f"{cert.get_notAfter()}", "B'%Y%m%d%H%M%SZ'")
    }


def create_stamp(data):

    def wrap_text(text, width, font):
        text_lines = []
        text_line = []
        text = text.replace('\n', ' [br] ')
        words = text.split()
        font_size = font.getsize(text)

        for word in words:
            if word == '[br]':
                text_lines.append(' '.join(text_line))
                text_line = []
                continue
            text_line.append(word)
            w, h = font.getsize(' '.join(text_line))
            if w > width:
                text_line.pop()
                text_lines.append(' '.join(text_line))
                text_line = [word]

        if len(text_line) > 0:
            text_lines.append(' '.join(text_line))

        return text_lines

    stamp_image = Image.new('RGBA', (350, 150), (0, 0, 0, 0))
    draw = ImageDraw.Draw(stamp_image)
    font = ImageFont.truetype('Stencil.ttf', 14)

    line_height = font.getsize('SAMPLE')[1]
    vertical_position = 10

    for key, value in data.items():
        info_str = f'{key}: {value}'
        substr = wrap_text(text=info_str, width=340, font=font)
        for ss in substr:
            draw.text((10, vertical_position), ss, font=font, fill=(20,20,150))
            vertical_position += line_height

    # Border
    border_color = (20, 20, 150)
    border_width = 2
    border_box = [(0, 0), (350 - 1, 150 - 1)]
    draw.rectangle(border_box, outline=border_color, width=border_width)

    # Save the stamp image
    buffer = BytesIO()
    stamp_image.save(buffer, format='PDF', resolution=100.0)
    return buffer.getvalue()


def print_stamp(stamp, pdf):
    global pdf_data
    pdf = PdfReader(BytesIO(pdf))
    stamp_pdf = PdfReader(BytesIO(stamp))
    
    num_pages = len(pdf.pages)
    last_page = PageMerge(pdf.pages[num_pages-1])
    stamp = last_page.add(stamp_pdf.pages[0])

    last_page_x, last_page_y, last_page_w, last_page_h = map(
        float, pdf.pages[num_pages - 1].MediaBox)
    stamp_x, stamp_y, stamp_w, stamp_h = map(float, stamp_pdf.pages[0].MediaBox)
    stamp.x = last_page_w - stamp_w
    stamp.y = last_page_y

    last_page.render()
    buffer_data = BytesIO()

    PdfWriter().write(buffer_data, pdf)
    pdf_data = buffer_data.getvalue()


@app.get("/download")
async def download_page():
    global pdf_data
    return StreamingResponse(BytesIO(pdf_data),
    media_type="application/pdf",
    headers={
        "Content-Disposition": "attachment; filename=output.pdf"
    })


def get_certificates(self):
    """
    https://github.com/pyca/pyopenssl/pull/367/files#r67300900

    Returns all certificates for the PKCS7 structure, if present. Only
    objects of type ``signedData`` or ``signedAndEnvelopedData`` can embed
    certificates.

    :return: The certificates in the PKCS7, or :const:`None` if
        there are none.
    :rtype: :class:`tuple` of :class:`X509` or :const:`None`
    """
    certs = _ffi.NULL
    if self.type_is_signed():
        certs = self._pkcs7.d.sign.cert
    elif self.type_is_signedAndEnveloped():
        certs = self._pkcs7.d.signed_and_enveloped.cert

    pycerts = []
    for i in range(_lib.sk_X509_num(certs)):
        pycert = X509()
        pycert._x509 = _lib.X509_dup(_lib.sk_X509_value(certs, i))
        pycerts.append(pycert)

    if not pycerts:
        return None
    return tuple(pycerts)