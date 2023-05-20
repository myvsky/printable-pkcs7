import time

from playwright.async_api import async_playwright

from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

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
    # We'll get the input files as soon as the user submits them in HTML
    pdf_contents = await pdf_file.read()
    sig_contents = await sig_file.read()

    # When it's posted, we get information for further stamp creation
    stamp_info = await parse_sig(pdf_contents, sig_contents)
    create_stamp(stamp_info)
    return {"message": "Files uploaded and processed successfully"}


async def parse_sig(pdf_file, sig_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page()

        await page.goto('https://www.gosuslugi.ru/eds')

        # Wait for the input elements to appear in the DOM
        await page.wait_for_selector('body')
        input_element = await page.query_selector_all('input')

        # Fill in the input elements with the file contents
        await input_element[1].set_input_files({'name': 'file.pdf', 'mimeType': 'application/pdf', 'buffer': pdf_file})
        time.sleep(2)
        await input_element[2].set_input_files({'name': 'file.sig', 'mimeType': 'application/octet-stream', 'buffer': sig_file})

        await page.wait_for_selector("//a[@ng-bind='btnText']")
        button_el = await page.query_selector("//a[@ng-bind='btnText']")
        await button_el.click()

        # Wait for conent we will extract to be loaded
        await page.wait_for_selector('//div[@class="row ng-scope"]')

        # Select all the elements that contain information about signature
        info = await page.query_selector_all('//*[@class="span_11 plain-text ng-binding"]')

        parsed_dict = {
            "Статус подписи": await info[0].text_content(),
            "Владелец сертификата": await info[2].text_content(),
            "Издатель сертификата": await info[3].text_content(),
            "Серийный номер": await info[4].text_content(),
            "Действителен": await info[5].text_content()
        }
        await browser.close()

        return parsed_dict

def create_stamp(data: dict):
    temp_img = Image.new('RGB', (300, 100), 'white')
    font = ImageFont.truetype('Stencil.ttf', size=10)
    draw = ImageDraw.Draw(temp_img)

    text_pos = {
        "Статус подписи": (10, 10),
        "Владелец сертификата": (10, 40),
        "Издатель сертификата": (10, 55),
        "Серийный номер": (10, 70),
        "Действителен": (10, 85)
    }

    for key, value in data.items():
        pos = text_pos.get(key)
        if pos:
            draw.text(pos, f'{key}: {value}', fill='black', font=font)

    temp_img.save('stamp.png')