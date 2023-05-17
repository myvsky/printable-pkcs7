import time

from playwright.async_api import async_playwright

import logging

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
    return HTMLResponse(content=html_content)


@app.post("/upload")
async def collect_upload(sig_file: UploadFile = File(...), pdf_file: UploadFile = File(...)):
    # We'll get the input files as soon as the user submits them in HTML
    pdf_contents = await pdf_file.read()
    sig_contents = await sig_file.read()

    # When it's posted, we get information for further stamp creation
    await parse_sig(pdf_contents, sig_contents)
    return {"message": "Files uploaded and processed successfully"}


async def parse_sig(pdf_file, sig_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto('https://www.gosuslugi.ru/eds')

        # Wait for the input elements to appear in the DOM
        await page.wait_for_selector('body')
        logging.info("Gosuslugi page loaded successfully")
        input_elements = await page.query_selector_all('input')

        # Select the second and third input elements
        input_element_2 = input_elements[1]
        input_element_3 = input_elements[2]

        # Fill in the input elements with the file contents
        await input_element_2.set_input_files({'name': 'file.pdf', 'mimeType': 'application/pdf', 'buffer': pdf_file})
        
        # TO-DO: MAKE A NORMAL DELAY THERE
        time.sleep(1)
        await input_element_3.set_input_files({'name': 'file.sig', 'mimeType': 'application/octet-stream', 'buffer': sig_file})

        await page.wait_for_selector("//a[@ng-bind='btnText']")
        button_el = await page.query_selector("//a[@ng-bind='btnText']")
        await button_el.click()

        # Wait for conent we will extract to be loaded
        await page.wait_for_selector('//div[@class="row ng-scope"]')

        output_html = await page.content()
        await browser.close()

        open("output.html", "w", encoding='utf-8').write(output_html)
