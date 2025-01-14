## Invoice Extractor For Frappe ERPNext

#BY : ABHIJEET SUTAR

## Introduction

The Invoice Extractor app is designed to seamlessly extract information from customer purchase orders and automatically generate corresponding sales orders based on the extracted data. Leveraging the power of Google Gemini AI, the app processes PDF purchase orders to accurately extract key details such as purchase order numbers, dates, customer information, item details, quantities, unit of measure (UOM), and pricing.

The app includes a robust verification system to ensure data consistency. It checks whether the extracted items, units of measure (UOM), or customer records already exist in the master data. If any of the required information is missing, the app intelligently creates new records to fill the gaps, ensuring the master data remains complete and up-to-date.

By automating the extraction, verification, and record creation processes, Invoice Extractor streamlines sales order creation, reducing manual effort, minimizing errors, and enhancing operational efficiency.

## Installation Steps

1. Download the app using CLI.

	```bash
    bench get-app --branch [branch_name] https://github.com/AbhiSutar777/invoice_extractor.git 
    ```

2. Download the required libraries.
	Path/to/your/frappe-bench

	```bash
    pip install -r apps/invoice_extractor/requirements.txt
    ```

3. Install the app on your site
	
	```bash
	bench --site [your_site_name] install-app invoice_extractor
	```

