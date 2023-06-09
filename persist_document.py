#!/usr/bin/env python3
import os.path

import pdfplumber as pdfplumber
import PyPDF4 as PyPDF4
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

from app_types import PageData, PDFDocument
from utils import merge_hyphenated_words, fix_newlines, remove_multiple_newlines, clean_text, text_to_chunks, make_chain
from config import VECTOR_STORE_COLLECTION_NAME, VECTOR_STORE_PATH


def fill_pages_from_pdf(file_path: str, pdf_document: PDFDocument):
    """
    Extracts the text from each page of the PDF.
    :param file_path: - The path of the PDF file.
    :param pdf_document: - Python instance of document to fill.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with pdfplumber.open(file_path) as pdf:
        pdf_document.pages = []
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text.strip():  # Check if extracted text exists.
                pdf_document.pages.append(PageData(num=page_num, text=text))


def fill_metadata_from_pdf(file_path: str, pdf_document: PDFDocument):
    with open(file_path, 'rb') as pdf_file:
        reader = PyPDF4.PdfFileReader(pdf_file)
        metadata = reader.getDocumentInfo()

        pdf_document.title = metadata.get('/Title', '').strip()
        pdf_document.author = metadata.get('/Author', '').strip()
        pdf_document.creation_date = metadata.get('/CreationDate', '').strip()


def parse_pdf(file_path: str) -> PDFDocument:
    """
    Extracts the title and text from each page of the PDF.

    :param file_path: - The path of the PDF file.
    :return: The tuple containing the title and list of tuples with page numbers
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    pdf_document = PDFDocument(title='', author='', creation_date='', pages=[])
    fill_metadata_from_pdf(file_path, pdf_document)
    fill_pages_from_pdf(file_path, pdf_document)

    return pdf_document


if __name__ == "__main__":
    print("Parsing pdf")
    pdf_document = parse_pdf('./Nifty Bridge Terms of Service.pdf')

    print("Cleaning text")
    pdf_document.pages = clean_text(
        pages=pdf_document.pages,
        cleaning_functions=[
            merge_hyphenated_words,
            fix_newlines,
            remove_multiple_newlines,
        ]
    )

    print("Splitting text to chunks")
    document_chunks = text_to_chunks(pdf_document)

    embeddings = OpenAIEmbeddings()

    print("Embedding document")
    vector_store = Chroma.from_documents(
        document_chunks,
        embeddings,
        collection_name=VECTOR_STORE_COLLECTION_NAME,
        persist_directory=VECTOR_STORE_PATH
    )

    vector_store.persist()
