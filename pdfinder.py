import fitz  # PyMuPDF
import os

def search_text_in_pdf(pdf_path, search_text):
   # Open the PDF file
   pdf_document = fitz.open(pdf_path)

   # Loop through each page
   for page_num in range(pdf_document.page_count):
      page = pdf_document.load_page(page_num)
      text = page.get_text()

      # Search for the text
      if search_text in text:
         print(f"Found '{search_text}' on page {page_num + 1} in file '{pdf_path}'")

   # Close the PDF file
   pdf_document.close()


def iterate_over_directory(directory_path, search_text):

   # Loop through each file in the directory
   for file_name in os.listdir(directory_path):
      file_path = os.path.join(directory_path, file_name)

      # Check if the file is a PDF
      if file_path.endswith(".pdf"):
         search_text_in_pdf(file_path, search_text)


if __name__ == "__main__":
   directory_path = "D:\python\PDFinder\pdfs"
   search_text = "alat"

   iterate_over_directory(directory_path, search_text)