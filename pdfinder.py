import subprocess
from typing import List, Optional
import fitz  # PyMuPDF
import os
import re
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from functools import partial
import zipfile
import winreg

## TODO:
# - Add support for searching in ZIP files
# - Add an option to stop the search process

def get_default_pdf_viewer() -> Optional[str]:
	"""Returns the path to the default PDF viewer on Windows.

	Returns
	-------
	str
		Path to the default PDF viewer executable.
	"""
	try:
		with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r".pdf") as key:
			pdf_association = winreg.QueryValue(key, None)

		app_path_key = fr"{pdf_association}\shell\open\command"
		with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, app_path_key) as key:
			command = winreg.QueryValue(key, None)

		app_path = command.split('"')[1]
		if not os.path.exists(app_path):
			raise FileNotFoundError(f"File not found: {app_path}")

		return app_path
	except Exception as e:
		raise FileNotFoundError(f"Error finding default PDF viewer: {e}")  

def open_pdf_with_default_viewer(pdf_path, page=None) -> None:
	"""Open a PDF file on a specific page using the default PDF viewer.
	
	Parameters
	----------
	pdf_path : str
		Path to the PDF file.

	page : int
		Page number to open the PDF file at.
		Default is None.
	"""   
	try:
		try:
			default_pdf_viewer = get_default_pdf_viewer()
		except FileNotFoundError as e:
			subprocess.run(["start", pdf_path], shell=True)
			return
		if page is not None:
			subprocess.Popen([default_pdf_viewer, pdf_path, "/A", f"page={page}"])
		else:
			subprocess.Popen([default_pdf_viewer, pdf_path])
		return
	except FileNotFoundError as e:
		print(e)
		messagebox.showerror("Error", e)

def show_tooltip(widget: ctk.CTk, text: str, x_offset=70, y_offset=70) -> ctk.CTkLabel:
	"""Show a tooltip with the specified text at the given position.
	
	Parameters
	----------
	widget : ctk.CTkWidget
		The widget to attach the tooltip to.
		
	text : str
		The text to display in the tooltip.
		
	x_offset : int
		The horizontal offset from the widget.
		
	y_offset : int
		The vertical offset from the widget.
		
	Returns
	-------
	ctk.CTkLabel
		The tooltip label widget."""
	tooltip = ctk.CTkLabel(
		widget, 
		text=text, 
		bg_color='black', 
		fg_color='white', 
		text_color='black'
	)
	tooltip.place_forget()
	return tooltip


def hide_tooltip(tooltip: ctk.CTkLabel) -> None:
	"""Hide the tooltip widget.

	Parameters
	----------
	tooltip : ctk.CTkLabel
		The tooltip widget to hide."""
	if tooltip is not None:
		tooltip.destroy()


# Function to search for text in a PDF
def search_text_in_pdf(
	pdf_path: str,
	search_text: str,
	match_case: bool,
	whole_word: bool,
	results_text_widget: ctk.CTkTextbox,
	include_subdirs: bool
) -> int:
	"""Search for text in a PDF file and display the results in the text widget.
	
	Parameters
	----------
	pdf_path : str
		Path to the PDF file to search.
		
	search_text : str
		Text to search for in the PDF.
		
	match_case : bool
		Whether to match the case of the search text.
		
	whole_word : bool
		Whether to search for the whole word only.
		
	results_text_widget : ctk.CTkTextbox
		The text widget to display the search results.
		
	include_subdirs : bool
		Whether to include subdirectories in the search.
		
	Returns
	-------
	int
		The number of search results found in the PDF file."""
	pdf_document = fitz.open(pdf_path)
	pdf_file: Path = Path(pdf_path)

	results = []

	flags = 0 if match_case else re.IGNORECASE
	search_text = search_text.strip()
	search_text_original = search_text
	if whole_word:
		search_text = rf"\b{search_text}\b"

	# Loop through each page
	for page_num in range(pdf_document.page_count):
		page = pdf_document.load_page(page_num)

		blocks = page.get_text("blocks")

		for block_index, block in enumerate(blocks):
			block_text = block[4]

			# Search with the adjusted regex pattern
			if re.search(search_text, block_text, flags):
				if search_text_original is None:
					search_text_original = search_text
				results.append(
					(
						page_num + 1, 
						f"Found '{search_text_original}' on page {page_num + 1} of {pdf_file.name}"
					)
				)

	# Display results in the text widget
	if results:
		count = 0
		if include_subdirs:
			directory = os.path.dirname(pdf_file.absolute())
			results_text_widget.insert(ctk.END, f"\nDirectory: {directory}\n")
		tag_name = f"file_{pdf_file.name}"
		results_text_widget.insert(
			ctk.END, 
			f"\nResults in file: {pdf_file.name}\n", 
			tag_name
		)
		results_text_widget.tag_config(
			tag_name, 
			foreground="#0394fc", 
			underline=True
		)
		results_text_widget.tag_add(
			tag_name, 
			results_text_widget.index("end-2 lines"), 
			results_text_widget.index("end-1 lines")
		)
		results_text_widget.tag_bind(
			tag_name, 
			"<Button-1>", 
			partial(open_pdf, pdf_path)
		)
		results_text_widget.tag_bind(
			tag_name, 
			"<Enter>", 
			lambda e: results_text_widget.configure(cursor="hand2")
		)
		results_text_widget.tag_bind(
			tag_name, 
			"<Leave>", 
			lambda e: results_text_widget.configure(cursor="")
		)

		# Insert clickable text for each result
		for page_num, result in results:
			link_text = f"Page {page_num}"
			tag_name = f"page_{pdf_file.name}_{page_num}"
			results_text_widget.insert(ctk.END, f"{link_text}\n", tag_name)
			results_text_widget.tag_config(tag_name, foreground="#0394fc", underline=True)
			results_text_widget.tag_bind(
				tag_name,
				"<Button-1>",
				lambda e, p=page_num: open_pdf_with_default_viewer(pdf_path, page=p)
			)
			results_text_widget.tag_bind(
				tag_name, 
				"<Enter>", 
				lambda e: results_text_widget.configure(cursor="hand2")
			)
			results_text_widget.tag_bind(
				tag_name, 
				"<Leave>", 
				lambda e: results_text_widget.configure(cursor="")
			)
			count += 1

		pdf_document.close()
		return count
	else:
		pdf_document.close()
		return 0


def open_pdf(pdf_path: str, event=None) -> None:
	"""Open a PDF file with the default PDF viewer.
	
	Parameters
	----------
	pdf_path : str
		Path to the PDF file to open.
		
	event : tk.Event
		The event that triggered the function call."""
	os.startfile(pdf_path)

def open_pdfs_from_zip(
	zip_path: str, 
	search_text: str, 
	/,
	match_case: bool = False, 
	whole_word: bool = False, 
	results_text_widget: ctk.CTkTextbox = None, 
	include_subdirs: bool = False, 
	count: int = 0
) -> None:
	"""Open a ZIP file and search for text in each PDF file.
	
	Parameters
	----------
	zip_path : str
		Path to the ZIP file to open.
		
	search_text : str
		Text to search for in the PDF files.
		
	match_case : bool
		Whether to match the case of the search text.
		
	whole_word : bool
		Whether to search for the whole word only.
		
	results_text_widget : ctk.CTkTextbox
		The text widget to display the search results.
		
	include_subdirs : bool
		Whether to include subdirectories in the search.
		
	count : int
		The number of search results found in the PDF files."""
		
	try:
		with zipfile.ZipFile(zip_path, 'r') as zip_ref:
			pdf_files = [
				file for file in zip_ref.namelist() if file.endswith(".pdf")
			]

			for pdf_file in pdf_files:
				with zip_ref.open(pdf_file) as pdf_file_ref:
					search_text_in_pdf(pdf_file_ref, search_text, match_case, 
						whole_word, results_text_widget, include_subdirs)
	except FileNotFoundError:
		return f"Error: The file {zip_path} does not exist."
	except zipfile.BadZipFile:
		return "Error: The file is not a valid zip file."

def list_files_in_zip(zip_path: str) -> List[str]:
	"""List the files in a ZIP archive.

	Parameters
	----------
	zip_path : str
		Path to the ZIP file to list the files of.

	Returns
	-------
	list[str]
		A list of file names in the ZIP archive."""
	try:
		with zipfile.ZipFile(zip_path, 'r') as zip_ref:
			files = [
				file for file in zip_ref.namelist() if file.endswith(".pdf")
			]
			return files
	except FileNotFoundError:
		raise FileNotFoundError(f"Error: The file {zip_path} does not exist")
	except zipfile.BadZipFile:
		raise zipfile.BadZipFile("Error: The file is not a valid zip file")
	finally:
		return []

# Function to iterate over directory and search text in each PDF
def iterate_over_directory(
	directory_path: str, 
	search_text: str, 
	match_case: bool, 
	whole_word: bool, 
	include_subdirs: bool, 
	zip_var: bool, 
	results_text_widget: ctk.CTkTextbox, 
	progress_bar: ctk.CTkProgressBar, 
	search_button: ctk.CTkButton
):
	results_text_widget.delete(1.0, ctk.END)  # Clear previous results
	count = 0
	pdf_files = []
	zip_files = []
	if include_subdirs:
		for root, dirs, files in os.walk(directory_path):
			pdf_files.extend(
				os.path.join(root, file) 
				for file in files if file.endswith(".pdf")
			)
			if zip_var:
				zip_files.extend(
					os.path.join(root, file) 
					for file in files if file.endswith(".zip")
				)
	else:
		pdf_files = [
			os.path.join(directory_path, file_name) 
			for file_name in os.listdir(directory_path) 
			if file_name.endswith(".pdf")
		]
		if zip_var:
			zip_files = [
				os.path.join(directory_path, file_name) 
				for file_name in os.listdir(directory_path) 
				if file_name.endswith(".zip")
			]

	total_pdf_files = len(pdf_files)
	if len(zip_files) != 0:
		for zip_file in zip_files:
			total_pdf_files += len(list_files_in_zip(zip_file))
			open_pdfs_from_zip(
				zip_file, 
				search_text, 
				match_case, 
				whole_word, 
				results_text_widget, 
				include_subdirs, 
				count
			)

	if total_pdf_files == 0:
		messagebox.showinfo(
			"No PDFs Found", 
			"No PDF files were found in the selected directory."
		)
		progress_bar.set(0)  # Reset progress bar
		search_button.configure(state="normal", text="Search")
		return

	# Iterate over each PDF and update the progress bar
	for index, file_path in enumerate(pdf_files):
		count += search_text_in_pdf(
			file_path, 
			search_text, 
			match_case, 
			whole_word, 
			results_text_widget, 
			include_subdirs
		)

		# Update progress bar
		progress = (index + 1) / total_pdf_files  # Calculate progress as a fraction
		progress_bar.set(progress)

	search_button.configure(state="normal", text="Search")  # Re-enable search button after search is done

	if count == 0:
		results_text_widget.insert(
			ctk.END, 
			f"No results found for '{search_text}'\n"
		)
		messagebox.showinfo(
			"No PDFs Found", 
			"No PDF files were found in the selected directory."
		)
		progress_bar.set(0)  # Reset progress bar
		search_button.configure(state="normal")  # Re-enable search button
		return

	messagebox.showinfo("Finished searching", f"{count} results were found.")


# Function to select directory using a file dialog
def select_directory(entry_widget: ctk.CTkEntry):
	"""Select a directory using a file dialog and set the entry widget value.
	
	Parameters
	----------
	entry_widget : ctk.CTkEntry
		The entry widget to set the directory path to."""
	directory_path = filedialog.askdirectory()
	entry_widget.delete(0, ctk.END)  # Clear current entry
	entry_widget.insert(0, directory_path)


# Function to handle search in a separate thread to keep the GUI responsive
def threaded_search(
	dir_entry: ctk.CTkEntry, 
	term_entry: ctk.CTkEntry, 
	match_case_var: ctk.BooleanVar, 
	whole_word_var: ctk.BooleanVar, 
	subdir_var: ctk.BooleanVar, 
	zip_var: ctk.BooleanVar, 
	results_text_widget: ctk.CTkTextbox, 
	progress_bar: ctk.CTkProgressBar, 
	search_button: ctk.CTkButton
):
	"""Perform the search in a separate thread to keep the GUI responsive.
	
	Parameters
	----------
	dir_entry : ctk.CTkEntry
		The entry widget containing the directory path.
		
	term_entry : ctk.CTkEntry
		The entry widget containing the search term.
		
	match_case_var : ctk.BooleanVar
		The variable for the match case checkbox.
		
	whole_word_var : ctk.BooleanVar
		The variable for the whole word checkbox.
		
	subdir_var : ctk.BooleanVar
		The variable for the include subdirectories checkbox.
		
	zip_var : ctk.BooleanVar
		The variable for the search in ZIP files checkbox.
		
	results_text_widget : ctk.CTkTextbox
		The text widget to display the search results.
		
	progress_bar : ctk.CTkProgressBar
		The progress bar widget.
		
	search_button : ctk.CTkButton
		The search button widget."""
	
	directory_path = dir_entry.get()
	search_term = term_entry.get()

	match_case = match_case_var.get()
	whole_word = whole_word_var.get()
	include_subdirs = subdir_var.get()
	zip_var = zip_var.get()

	# Validate input
	if not directory_path or not search_term:
		messagebox.showwarning("Input Error", "Both directory and search term must be provided.")
		search_button.configure(state="normal", text="Search")  # Re-enable search button
		return

	if not os.path.isdir(directory_path):
		messagebox.showerror("Directory Error", "The selected directory does not exist.")
		search_button.configure(state="normal", text="Search")  # Re-enable search button
		return

	# Start searching (in a separate thread)
	search_thread = threading.Thread(
		target=iterate_over_directory, 
		args=(
			directory_path, 
			search_term, 
			match_case, 
			whole_word, 
			include_subdirs, 
			zip_var, 
			results_text_widget, 
			progress_bar, 
			search_button
		)
	)
	search_thread.start()


# GUI setup with CustomTkinter
def setup_gui():
	ctk.set_appearance_mode("dark")
	ctk.set_default_color_theme("blue")

	root = ctk.CTk()  # Use CTk instead of Tk for the main window
	root.title("PDF Text Finder")
	root.geometry("800x550")  # Set the window size
	heading_font = ctk.CTkFont(family="Arial", size=14, weight='bold')
	regular_font = ctk.CTkFont(family="Arial", size=14, weight='bold')

	# Directory label and entry
	dir_label = ctk.CTkLabel(root, text="Select Directory:", font=heading_font)
	dir_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

	dir_entry = ctk.CTkEntry(root, width=400)
	dir_entry.grid(row=0, column=1, padx=10, pady=10)

	dir_button = ctk.CTkButton(
		root, 
		text="Browse", 
		command=lambda: select_directory(dir_entry), 
		font=regular_font
	)
	dir_button.grid(row=0, column=2, padx=10, pady=10)

	# Search term label and entry
	term_label = ctk.CTkLabel(root, text="Search Term:", font=heading_font)
	term_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

	term_entry = ctk.CTkEntry(root, width=400)
	term_entry.grid(row=1, column=1, padx=10, pady=10)

	# Match case, whole word and include subfolder checkboxes
	match_case_var = ctk.BooleanVar()
	match_case_check = ctk.CTkCheckBox(
		root, 
		text="Match Case", 
		variable=match_case_var, 
		font=regular_font
	)
	match_case_check.grid(row=2, column=0, padx=10, pady=10, sticky="w")

	whole_word_var = ctk.BooleanVar()
	whole_word_check = ctk.CTkCheckBox(
		root, 
		text="Whole Word", 
		variable=whole_word_var, 
		font=regular_font
	)
	whole_word_check.grid(row=2, column=1, padx=10, pady=10, sticky="w")

	subdir_var = ctk.BooleanVar()
	subdir_check = ctk.CTkCheckBox(
		root, 
		text="Include subdirectories", 
		variable=subdir_var, 
		font=regular_font
	)
	subdir_check.grid(row=3, column=0, padx=10, pady=10, sticky="w")

	zip_var = ctk.BooleanVar()
	zip_check = ctk.CTkCheckBox(
		root, 
		text="Search in ZIP files", 
		variable=zip_var, 
		font=regular_font
	)
	zip_check.grid(row=3, column=1, padx=10, pady=10, sticky="w")

	tooltip = None

	# Search button
	def update_tooltip(e):
		if tooltip is not None:
			tooltip.place(x=370, y=150)

	def on_enter(e):
		nonlocal tooltip
		tooltip = show_tooltip(root, "This feature is currently unavailable")
		update_tooltip(e)
		zip_check.bind("<Motion>", update_tooltip)

	def on_leave(e):
		nonlocal tooltip
		hide_tooltip(tooltip)
		tooltip = None
		zip_check.bind("<Motion>")

	zip_check.bind("<Enter>", on_enter)
	zip_check.bind("<Leave>", on_leave)
	search_button = ctk.CTkButton(
		root, 
		text="Search", 
		font=regular_font, 
		hover_color="#104163", 
		command=lambda: [
			search_button.configure(state="disabled", text="Stop"), 
			threaded_search(
				dir_entry, 
				term_entry, 
				match_case_var, 
				whole_word_var, 
				subdir_var, 
				zip_var, 
				results_text, 
				progress_bar, 
				search_button
			)
		]
	)
	search_button.grid(row=3, column=2, padx=10, pady=10)

	# Progress bar
	progress_bar = ctk.CTkProgressBar(root, width=500)
	progress_bar.grid(row=5, column=0, columnspan=4, padx=10, pady=10)
	progress_bar.set(0)  # Initialize progress bar at 0%

	# Results text widget
	results_text = ctk.CTkTextbox(root, width=600, height=300, font=regular_font)
	results_text.grid(row=6, column=0, columnspan=4, padx=10, pady=10)
	root.bind(
		'<Return>', 
		lambda event: [
			search_button.configure(state="disabled"), 
			threaded_search(
				dir_entry, 
				term_entry, 
				match_case_var, 
				whole_word_var, 
				subdir_var, 
				results_text, 
				progress_bar, 
				search_button
			)
		]
	)

	results_text.tag_config('tag', foreground="#0394fc", underline=True)
	root.mainloop()


if __name__ == "__main__":
	setup_gui()
