# Copyright (c) 2024, Abhijeet Sutar and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class UploadCustomerPO(Document):
	pass

import frappe
import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import csv
import io
import re 
from frappe.utils import get_bench_path
from frappe import throw

from PyPDF2 import PdfReader, PdfWriter

# # Load environment variables
load_dotenv()  # Load all environment variables including GOOGLE_API_KEY

# google_api_key = frappe.db.get_value("Google API", {'name': 'Gemini 1.5 Flash'}, "api_key")
google_api_key = frappe.db.get_value("Google API", {'default': 1}, "api_key")

# Set up Google Gemini API key
# genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
genai.configure(api_key=google_api_key)

# Function to split the PDF into chunks
def split_pdf(file_path, chunk_size=10):
    """Splits a PDF file into smaller chunks of the specified size."""
    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    chunks = []

    for i in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        chunk_path = f"{file_path}_chunk_{i//chunk_size + 1}.pdf"

        for j in range(i, min(i + chunk_size, total_pages)):
            writer.add_page(reader.pages[j])

        with open(chunk_path, "wb") as chunk_file:
            writer.write(chunk_file)
        chunks.append(chunk_path)

    return chunks

# Function to upload the PDF to Gemini
def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    # frappe.msgprint(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

# Function to wait for files to become active after upload
def wait_for_files_active(files):
    """Waits for the given files to be active."""
    # # frappe.msgprint("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            # frappe.msgprint(".", end="", flush=True)
            time.sleep(10)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
    # frappe.msgprint("...all files ready")

# # # Gemini-1.5.Flash model------------------------------------------------------------------------------------------------------------------------------
@frappe.whitelist()
def process_po_data(doc, method=None):
    # # Get the attached file (PDF) from the 'attach_copy' field
    if not doc.attach_copy:
        frappe.throw("Please upload a PO copy in the 'attach_copy' field.")

    # # Get the file URL from the document
    file_url = doc.attach_copy

    # # Determine if the file is private or public
    is_private = file_url.startswith('/private/files/')
    if is_private:
        file_name = file_url.split("/private/files/")[1]
    elif file_url.startswith('/files/'):
        file_name = file_url.split("/files/")[1]
    else:
        frappe.throw("Unsupported file location.")

    # # Construct the file path using get_bench_path and get_path
    file_path = get_bench_path() + "/sites/" + frappe.utils.get_path('private' if is_private else 'public', 'files', file_name)[2:]

    # # Ensure the file exists
    if not frappe.db.exists("File", {'file_name': file_name}):
        frappe.throw(f"File {doc.attach_copy} does not exist.")

    # Split the PDF into smaller chunks
    chunks = split_pdf(file_path, chunk_size=10)
    gemini_files = []

    # Upload each chunk to Google Gemini
    for chunk in chunks:
        gemini_file = upload_to_gemini(chunk, mime_type="application/pdf")
        gemini_files.append(gemini_file)

    # Wait for all chunks to be processed
    wait_for_files_active(gemini_files)

    # Process each chunk with the Gemini model
    item_table = []
    customer_name, po_no, po_date, required_date = None, None, None, None

    # # Generate content using the Gemini model with the uploaded file
    # try:
    for gemini_file in gemini_files:
        # # Use the "gemini-1.5-flash" model
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            # generation_config={
            #     "temperature": 0,
            #     "top_p": 0.95,
            #     "top_k": 40,
            #     "max_output_tokens": 15000,  # Reduced token limit to avoid large responses
            #     "response_mime_type": "application/json",
            # },
            generation_config = {
              "temperature": 0,
              "top_p": 0.95,
              "top_k": 40,
              "max_output_tokens": 8192,
              "response_mime_type": "application/json",
            }
        )

        # # Define the prompt with the file
        prompt = {
            "role": "user",
            "parts": [
                gemini_file,  # Attach the uploaded file
                # """Extract a Customer name (entity who raised the Purchase Order), Purchase Order Number, Purchase Order Issue Date, Required By Date, 
                # and an Item table in CSV format with columns: Item Name or Item Description, Quantity, Rate or Discounted Rate, Unit Of Measure. Provide specific values only. 
                # Save data in customer_name,po_no,po_date,required_date,item_table. Extract all dates in 'yyyy/mm/dd' format. 
                # Find Item Code from the whole description if item Name not available. If Item Code not available get Item Name. item Name can be longer and can contain alphabets."""

                """Extract a Customer name (entity who raised the Purchase Order), Purchase Order Number, Purchase Order Issue Date, Required By Date, 
                and an Item table in CSV format with columns: Item Code or Part Number, Quantity, Rate or Discounted Rate, Unit Of Measure. Provide specific values only. 
                Save data in customer_name,po_no,po_date,required_date,item_table. Extract all dates in 'yyyy/mm/dd' format. 
                Find item Name from the whole description if Item Code not available. Item Name can be longer and can contain alphabets."""

            ]
        }

        # # Generate the response
        chat_session = model.start_chat(history=[prompt])
        response = chat_session.send_message("Start processing")

        # # Log the raw response text for debugging
        response_text = response.text
        frappe.logger().info(f"Raw response from Gemini: {response_text[:1000]}")  # Log first 1000 chars for inspection

        # # Try to parse the JSON response
        try:
            po_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            frappe.throw(f"Failed to parse Gemini response: {str(e)}. Raw response: {response_text[:500]}")
        
        # # Check if the JSON is valid and complete
        if 'customer_name' not in po_data or 'po_no' not in po_data or 'item_table' not in po_data:
            frappe.throw(f"Response from Gemini seems incomplete. Raw response: {response_text[:1000]}")

        # Extract individual variables from JSON response
        customer_name = po_data.get("customer_name", "N/A")
        po_no = po_data.get("po_no", "N/A")
        po_date = po_data.get("po_date", "N/A")
        required_date = po_data.get("required_date", "N/A")
        item_table_csv = po_data.get("item_table", "N/A")

        ## Append data in item_table
        if item_table_csv != "N/A":
            try:
                # # Check if item_table_csv is already a list or needs conversion to CSV format
                if isinstance(item_table_csv, list):
                    # Convert the list to CSV string
                    output = io.StringIO()
                    csv_writer = csv.writer(output)
                    # Write header with underscores and lowercase
                    csv_writer.writerow(["item_name", "qty", "rate", "uom"])
                    # Write each item
                    for item in item_table_csv:
                        csv_writer.writerow([
                            # item.get("Item Name or Item Description"),
                            item.get("Item Code or Part Number"),
                            item.get("Quantity"),
                            item.get("Rate or Discounted Rate"),
                            item.get("Unit Of Measure")
                        ])
                    item_table_csv = output.getvalue()  # Get the CSV string
                
                # # Use csv.reader to parse the CSV data
                csv_reader = csv.reader(io.StringIO(item_table_csv))
                header = next(csv_reader)  # Get the header
                for row in csv_reader:
                    item_dict = dict(zip(header, row))  # Create a dictionary for each row
                    item_table.append(item_dict)
    
            except Exception as e:
                frappe.throw(f"Error processing item table CSV: {e}")

    return customer_name, po_no, po_date, required_date, item_table

@frappe.whitelist()
def extract_po_no(doc, method=None):
    # # Get the attached file (PDF) from the 'attach_copy' field
    if not doc.attach_copy:
        frappe.throw("Please upload a PO copy in the 'attach_copy' field.")

    # # Get the file URL from the document
    file_url = doc.attach_copy

    # # Determine if the file is private or public
    is_private = file_url.startswith('/private/files/')
    if is_private:
        file_name = file_url.split("/private/files/")[1]
    elif file_url.startswith('/files/'):
        file_name = file_url.split("/files/")[1]
    else:
        frappe.throw("Unsupported file location.")

    # # Construct the file path using get_bench_path and get_path
    file_path = get_bench_path() + "/sites/" + frappe.utils.get_path('private' if is_private else 'public', 'files', file_name)[2:]

    # # Ensure the file exists
    if not frappe.db.exists("File", {'file_name': file_name}):
        frappe.throw(f"File {doc.attach_copy} does not exist.")

    # Split the PDF into smaller chunks
    chunks = split_pdf(file_path, chunk_size=10)
    gemini_files = []

    # Upload each chunk to Google Gemini
    for chunk in chunks:
        gemini_file = upload_to_gemini(chunk, mime_type="application/pdf")
        gemini_files.append(gemini_file)

    # Wait for all chunks to be processed
    wait_for_files_active(gemini_files)

    # Process each chunk with the Gemini model
    item_table = []
    customer_name, po_no, po_date, required_date = None, None, None, None

    # # Generate content using the Gemini model with the uploaded file
    # try:
    for gemini_file in gemini_files:
        # # Use the "gemini-1.5-flash" model
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 15000,  # Reduced token limit to avoid large responses
                "response_mime_type": "application/json",
            },
        )

        # # Define the prompt with the file
        prompt = {
            "role": "user",
            "parts": [
                gemini_file,  # Attach the uploaded file
                # """Extract a Customer name (entity who raised the Purchase Order), Purchase Order Number, Purchase Order Issue Date, Required By Date, 
                # and an Item table in CSV format with columns: Item Name or Item Description, Quantity, Rate or Discounted Rate, Unit Of Measure. Provide specific values only. 
                # Save data in customer_name,po_no,po_date,required_date,item_table. Extract all dates in 'yyyy/mm/dd' format. 
                # Find Item Code from the whole description if item Name not available. It Item Code not available get Item Name. item Name can be longer and can contain alphabets."""

                """Extract a Customer name (entity who raised the Purchase Order), Purchase Order Number and Purchase Order Issue Date from the attached file and 
                Save data in customer_name, po_no and po_date. Extract all dates in 'yyyy/mm/dd' format."""

            ]
        }

        # # Generate the response
        chat_session = model.start_chat(history=[prompt])
        response = chat_session.send_message("Start processing")

        # # Log the raw response text for debugging
        response_text = response.text
        frappe.logger().info(f"Raw response from Gemini: {response_text[:1000]}")  # Log first 1000 chars for inspection

        # # Try to parse the JSON response
        try:
            po_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            frappe.throw(f"Failed to parse Gemini response: {str(e)}. Raw response: {response_text[:500]}")
        
        # # Check if the JSON is valid and complete
        if 'po_no' not in po_data:
            frappe.throw(f"Response from Gemini seems incomplete. Raw response: {response_text[:1000]}")

        # Extract individual variables from JSON response
        po_no = po_data.get("po_no", "N/A")
        po_date = po_data.get("po_date", "N/A")
        customer_name = po_data.get("customer_name", "N/A")

    return customer_name, po_no, po_date

# # # Extract PO NUMBER-----------------------------------------------------------------------------------------------------------------------------
def set_po_no_as_doc_name(doc, method=None):
    if doc.is_new():
        # # # Parse the incoming document if it's a string
        # doc = frappe.parse_json(doc)
    
        # # # Load the actual Document object using its doctype and name
        # po_doc = frappe.get_doc(doc.get('doctype'), doc.get('name'))
    
        # # Call the process_po_data function to extract the data
        customer_name, po_no, po_date = extract_po_no(doc)
    
        doc.name = po_no
        doc.customer = customer_name
        doc.po_number = po_no
        doc.po_date = po_date
        # doc.save()


# # # Create Sales Order------------------------------------------------------------------------------------------------------------------------------
@frappe.whitelist()
def create_sales_order_from_po(doc, method=None):
    # # Parse the incoming document if it's a string
    doc = frappe.parse_json(doc)

    # # Load the actual Document object using its doctype and name
    doc = frappe.get_doc(doc.get('doctype'), doc.get('name'))

    # # Call the process_po_data function to extract the data
    customer_name, po_no, po_date, required_date, item_table = process_po_data(doc)

    # # Now call the create_sales_order with the extracted values
    create_sales_order(customer_name, po_no, po_date, required_date, item_table)


def create_sales_order(customer_name, po_no, po_date, required_date, item_table):
    """
    Function to create a Sales Order from the extracted PO data.
    """

    # # Convert required_date to a date object for comparison
    required_date = frappe.utils.getdate(required_date)
    today = frappe.utils.getdate(frappe.utils.today())

    # # frappe.msgprint(f"Converted Required Date: {required_date}")
    
    # # Compare the required_date with today's date
    if required_date < today:
        customer_requirement_date = today
    else:
        customer_requirement_date = required_date

    # frappe.msgprint(f"Customer Requirement Date: {customer_requirement_date}")

    # # Check if customer exists, if not create new
    customer = get_or_create_customer(customer_name)

    # # Prepare item table for sales order
    items_list = []
    for idx, item in enumerate(item_table):
    # # for item in item_table:
        item_name = item.get("item_name")
        qty = float(item.get("qty", 0))  # Default to 0 if quantity is missing
        rate = item.get("rate", "0")  # Default to "0" if rate is missing
        uom = item.get("uom", "Nos")  # Default to "Nos" if UOM is missing

        # # Clean the rate by removing non-numeric characters and convert to float
        rate_cleaned = re.sub(r'[^\d.]', '', str(rate))

        # # If rate is null then assign 0 and print message..
        if rate_cleaned:
            rate_cleaned = float(rate_cleaned)
        else:
            # Handle the case where rate is empty or invalid
            frappe.msgprint(f"Invalid rate value for item: {item.get('item_name', 'Unknown')}")
            rate_cleaned = 0 

        # # Check if item exists, if not create new
        item_code = get_or_create_item(item_name)

        # # Ensure UOM exists, if not create it
        uom_name = get_or_create_uom(uom)  # Pass the cleaned UOM

        # # Add the item to the sales order item list
        items_list.append({
            "item_code": item_code,
            "qty": qty,
            "rate": rate_cleaned,  # Convert cleaned rate to float
            "uom": uom_name,  # Include UOM in the Sales Order Item
            "delivery_date" : customer_requirement_date
        })

    # # Create a new Sales Order
    sales_order = frappe.get_doc({
        "doctype": "Sales Order",
        "customer": customer.name,
        "po_no": po_no,
        "po_date": frappe.utils.getdate(po_date),
        "delivery_date": customer_requirement_date,
        "items": items_list,
    })

    # # Save and optionally submit the Sales Order
    sales_order.save()
    # sales_order.submit()  # Uncomment to submit the Sales Order

    # # Show success message
    frappe.msgprint(
        f"Sales Forecast Upload Records created successfully. Click on "
        f"<a href='http://127.0.0.1:8000/app/sales-order/{sales_order.name}' target='_blank'>{sales_order.name}</a> to view the Sales Order."
    )
    return sales_order.name


# # # Check If UOM exists in system or not------------------------------------------------------------------------------------------------------------------------------
def get_or_create_uom(uom_name):
    """
    Check if a Unit of Measure (UOM) exists by name, if not, create a new UOM.
    """
    # # Standardize the UOM name to uppercase for consistent checks
    uom_name = uom_name.upper()

    # # Check if the UOM exists in a case-insensitive way
    if not frappe.db.exists("UOM", {"uom_name": uom_name}):
        uom = frappe.new_doc("UOM")
        uom.uom_name = uom_name
        uom.save()
        frappe.msgprint(f"New UOM '{uom_name}' created.")

    return uom_name  # Return the standardized UOM name

# # # Check If Customer exists in system or not------------------------------------------------------------------------------------------------------------------------------
def get_or_create_customer(customer_name):
    """
    Check if a customer exists by name, if not, create a new customer.
    """
    if frappe.db.exists("Customer", {"customer_name": customer_name}):
        customer = frappe.get_doc("Customer", {"customer_name": customer_name})
    else:
        customer = frappe.new_doc("Customer")
        customer.customer_name = customer_name
        customer.save()
        # frappe.msgprint(f"New customer '{customer_name}' created.")

    return customer

# # # Check If Item exists in system or not------------------------------------------------------------------------------------------------------------------------------
def get_or_create_item(item_name):
    """
    Check if an item exists by name, if not, create a new item.
    """
    if frappe.db.exists("Item", {"item_name": ['like', f"%{item_name}%"]}):
        item = frappe.get_doc("Item", {"item_name": ['like', f"%{item_name}%"]})
    else:
        item = frappe.new_doc("Item")
        item.item_name = item_name
        item.item_code = item_name
        item.item_group = "All Item Groups"  # Set the default item group
        item.save()
        # frappe.msgprint(f"New item '{item_name}' created.")

    return item.item_code  # Return the item_code


###=====================================================================================================================================================
###=====================================================================================================================================================
###=====================================================================================================================================================

# ## PARTIALY WORKING...
# import frappe
# import os
# import google.generativeai as genai
# from dotenv import load_dotenv
# import tabula
# import re

# # Load environment variables
# load_dotenv()  # Load all environment variables including GOOGLE_API_KEY

# # Set up Google Gemini API key
# genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# # Function to load the Google Gemini model and get responses for each question
# def ask_gemini_for_po_data(extracted_content, question):
#     # Use Gemini 1.5 flash model
#     model = genai.GenerativeModel("gemini-1.5-flash")

#     # Ask the question with extracted text as input
#     response = model.generate_content([extracted_content, question])

#     # Return the response text
#     return response.text

# @frappe.whitelist()
# def process_po_data(doc, method=None):
#     # Get the attached file (PDF) from the 'attach_copy' field
#     if not doc.attach_copy:
#         frappe.throw("Please upload a PO copy in the 'attach_copy' field.")

#     # Get the file URL from the document
#     file_url = doc.attach_copy

#     # Determine if the file is private or public
#     is_private = file_url.startswith('/private/files/')
#     if is_private:
#         file_name = file_url.split("/private/files/")[1]
#     elif file_url.startswith('/files/'):
#         file_name = file_url.split("/files/")[1]
#     else:
#         frappe.throw("Unsupported file location.")

#     # Construct the file path using get_bench_path and get_path
#     file_path = frappe.utils.get_bench_path() + "/sites/" + frappe.utils.get_path('private' if is_private else 'public', 'files', file_name)[2:]

#     # Ensure the file exists
#     if not frappe.db.exists("File", {'file_name': file_name}):
#         frappe.throw(f"File {doc.attach_copy} does not exist.")

#     # Extract text from the PDF using Tabula
#     try:
#         extracted_content = tabula.read_pdf(file_path, pages="all", output_format="json")  # You can adjust the format
#         extracted_text = " ".join([str(item) for item in extracted_content])  # Convert JSON content to text

#     except Exception as e:
#         frappe.throw(f"Failed to extract content from PDF: {e}")

#     # # Define the questions to ask Google Gemini
#     questions = {
#         "PO Number": "What is the Purchase Order ID? Give only value.",
#         "PO Date": "What is the Purchase Order Date? Give only Date. change format to: YYYY-MM-DD",
#         "Required By": "What is the Requirement or Delivery Date? Give only values. change format to: YYYY-MM-DD ",
#         "Customer Name": "Who is the billd to? Give only Only Customer name.",
#         # "Customer Name": "Who is the Customer? find it from company or billing address of the po.Give only Only Customer name.",
#         "Items": "List the items in CSV format with headers: item_name, qty, rate, uom. No additional text, just values."
#     }
#     # questions = {
#     #     "PO Number": "Please provide the Purchase Order ID (only the ID, no additional text).",
#     #     "PO Date": "Please provide the Purchase Order Date (format: YYYY-MM-DD).",
#     #     "Required By": "Please provide the Requirement or Delivery Date (format: YYYY-MM-DD).",
#     #     "Customer Name": "Please provide the Customer Name, which can be found in the company's address or logo on the PO (only the name, no extra details).",
#     #     "Items": "Please list the items in CSV format with headers: item_name, qty, rate, uom. Only include the values, without any additional text."
#     # }


    
#     # Extracted data as variables
#     try:
#         po_number = ask_gemini_for_po_data(extracted_text, questions["PO Number"])
#         po_date = ask_gemini_for_po_data(extracted_text, questions["PO Date"])
#         required_by = ask_gemini_for_po_data(extracted_text, questions["Required By"])
#         customer_name = ask_gemini_for_po_data(extracted_text, questions["Customer Name"])
#         items_table_csv = ask_gemini_for_po_data(extracted_text, questions["Items"])
#     except Exception as e:
#         frappe.throw(f"Failed to get response from Google Gemini: {e}")

#     # Convert the CSV items table into a list of dictionaries, skipping headers
#     items_table = []
#     try:
#         # Split CSV lines and skip the first row (header)
#         items_rows = items_table_csv.split("\n")[1:]  # Skip the header row
#         for row in items_rows:
#             item_data = row.split(",")  # Assuming comma-separated values

#             # Ensure we have at least item_name, qty, rate, and uom
#             if len(item_data) >= 4:
#                 item_name = item_data[0].strip()
#                 qty = str(item_data[1].strip())
#                 rate = str(item_data[2].strip())
#                 uom = str(item_data[3].strip())

#                 # Append to the items list as a dictionary
#                 items_table.append({
#                     "item_name": item_name,
#                     "quantity": qty,
#                     "rate": rate,
#                     "uom": uom
#                 })
#             else:
#                 frappe.msgprint(f"Skipping invalid item row: {row}")
#     except Exception as e:
#         frappe.throw(f"Failed to process items table: {e}")

#     # Print each item in the list
#     frappe.msgprint(f"{customer_name}")
#     frappe.msgprint(f"{po_number}")
#     frappe.msgprint(f"{po_date}")
#     frappe.msgprint(f"{required_by}")
#     for item in items_table:
#         frappe.msgprint(f"Item: {item['item_name']}--{item['quantity']}--{item['rate']}--{item['uom']}")

#     ##Uncomment the Sales Order creation logic once the extracted data is confirmed
#     # try:
#     #     sales_order_name = create_sales_order({
#     #         "Customer Name": customer_name,
#     #         "PO Number": po_number,
#     #         "PO Date": po_date,
#     #         "Required By": required_by,
#     #         "Items": items_table
#     #     })
#     #     frappe.msgprint(f"Sales Order {sales_order_name} created successfully.")
#     # except Exception as e:
#     #     frappe.throw(f"Failed to create Sales Order: {e}")

#     return po_number, po_date, customer_name, items_table


# # def create_sales_order(po_data):
#     """
#     Function to create a Sales Order from the extracted PO data.
#     """
#     # Extract relevant data from the PO
#     customer_name = po_data.get("Customer Name")
#     customer_po = po_data.get("PO Number")
#     customer_po_date = po_data.get("PO Date")
#     customer_requirement_date = po_data.get("Required By")
#     items_data = po_data.get("Items")  # Assuming this is a list of dictionaries

#     # Check if customer exists, if not create new
#     customer = get_or_create_customer(customer_name)

#     # Prepare item table for sales order
#     items_list = []
#     for item in items_data:
#         item_name = item.get("item_name")
#         qty = item.get("quantity", 0)  # Default to 0 if quantity is missing
#         rate = item.get("rate", "0")  # Default to "0" if rate is missing
#         uom = item.get("uom", "Nos")  # Default to "Nos" if UOM is missing

#         # Clean the rate by removing non-numeric characters
#         rate_cleaned = re.sub(r'[^\d.]', '', str(rate))  # Remove any non-numeric characters except for decimal points

#         # Check if item exists, if not create new
#         item_code = get_or_create_item(item_name)

#         # Add the item to the sales order item list
#         items_list.append({
#             "item_code": item_code,
#             "qty": float(qty),
#             "rate": float(rate_cleaned),  # Convert cleaned rate to float
#             "uom": uom  # Include UOM in the Sales Order Item
#         })

#     # Create a new Sales Order
#     sales_order = frappe.get_doc({
#         "doctype": "Sales Order",
#         "customer": customer.name,
#         "po_no": customer_po,
#         "po_date": frappe.utils.getdate(customer_po_date),  # Convert PO date to date format
#         "delivery_date": frappe.utils.getdate(customer_requirement_date),  # Convert requirement date
#         "items": items_list,
#     })

#     # Save and optionally submit the Sales Order
#     sales_order.save()
#     # sales_order.submit()  # Uncomment to submit the Sales Order

#     return sales_order.name

# def create_sales_order(po_data):
#     """
#     Function to create a Sales Order from the extracted PO data.
#     """
#     # Extract relevant data from the PO
#     customer_name = po_data.get("Customer Name")
#     customer_po = po_data.get("PO Number")
#     customer_po_date = po_data.get("PO Date")
#     customer_requirement_date = po_data.get("Required By")
#     items_data = po_data.get("Items")  # Assuming this is a list of dictionaries

#     # Check if customer exists, if not create new
#     customer = get_or_create_customer(customer_name)

#     # Prepare item table for sales order
#     items_list = []
#     for item in items_data:
#         item_name = item.get("item_name")
#         qty = item.get("quantity", 0)  # Default to 0 if quantity is missing
#         rate = item.get("rate", "0")  # Default to "0" if rate is missing
#         uom = item.get("uom", "Nos")  # Default to "Nos" if UOM is missing

#         # Clean the rate by removing non-numeric characters
#         rate_cleaned = re.sub(r'[^\d.]', '', str(rate))  # Remove any non-numeric characters except for decimal points

#         # Check if item exists, if not create new
#         item_code = get_or_create_item(item_name)

#         # Ensure UOM exists, if not create it
#         get_or_create_uom(uom)

#         # Add the item to the sales order item list
#         items_list.append({
#             "item_code": item_code,
#             "qty": float(qty),
#             "rate": float(rate_cleaned),  # Convert cleaned rate to float
#             "uom": uom  # Include UOM in the Sales Order Item
#         })

#     if customer_requirement_date < frappe.utils.today():
#         customer_requirement_date = frappe.utils.today()
#     else:
#         customer_requirement_date = po_data.get("Required By")

#     # Create a new Sales Order
#     sales_order = frappe.get_doc({
#         "doctype": "Sales Order",
#         "customer": customer.name,
#         "po_no": customer_po,
#         "po_date": frappe.utils.getdate(customer_po_date),  # Convert PO date to date format
#         "delivery_date": frappe.utils.getdate(customer_requirement_date),  # Convert requirement date
#         "items": items_list,
#     })

#     # Save and optionally submit the Sales Order
#     sales_order.save()
#     # sales_order.submit()  # Uncomment to submit the Sales Order

#     return sales_order.name

# def get_or_create_uom(uom_name):
#     """
#     Check if a Unit of Measure (UOM) exists by name, if not, create a new UOM.
#     """
#     if not frappe.db.exists("UOM", {"uom_name": uom_name}):
#         uom = frappe.new_doc("UOM")
#         uom.uom_name = uom_name
#         uom.save()
#         frappe.msgprint(f"New UOM '{uom_name}' created.")

# def get_or_create_customer(customer_name):
#     """
#     Check if a customer exists by name, if not, create a new customer.
#     """
#     if frappe.db.exists("Customer", {"customer_name": customer_name}):
#         customer = frappe.get_doc("Customer", {"customer_name": customer_name})
#     else:
#         customer = frappe.new_doc("Customer")
#         customer.customer_name = customer_name
#         customer.save()
#         frappe.msgprint(f"New customer '{customer_name}' created.")

#     return customer

# def get_or_create_item(item_name):
#     """
#     Check if an item exists by name, if not, create a new item.
#     """
#     if frappe.db.exists("Item", {"item_name": item_name}):
#         item = frappe.get_doc("Item", {"item_name": item_name})
#     else:
#         item = frappe.new_doc("Item")
#         item.item_name = item_name
#         item.item_code = item_name
#         item.item_group = "All Item Groups"  # Set the default item group
#         item.save()
#         frappe.msgprint(f"New item '{item_name}' created.")

#     return item.item_code  # Return the item_code




###=====================================================================================================================================================
###=====================================================================================================================================================
###=====================================================================================================================================================
