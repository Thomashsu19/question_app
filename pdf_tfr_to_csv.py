import os
import camelot
import pandas as pd

# Define the PDF file path
pdf_file_path = '115年外匯內部證照第二次檢定題庫(本題庫部份內容、選項出題時會稍作變化，請同仁熟讀!).pdf'

# Create a directory to save the CSV files
output_dir = 'extracted_tables'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created directory: {output_dir}")

try:
    # Extract tables from the PDF
    # Using 'lattice' flavor for tables with clear borders
    # You can try 'stream' flavor if 'lattice' doesn't work well for your PDF
    print(f"Extracting tables from {pdf_file_path}...")
    tables = camelot.read_pdf(pdf_file_path, pages='all', flavor='lattice')
    print(f"Found {len(tables)} tables.")

    if tables:
        # Save each table as a CSV file
        for i, table in enumerate(tables):
            csv_output_path = os.path.join(output_dir, f'table_{i+1}.csv')
            table.to_csv(csv_output_path, index=False, encoding='utf-8')
            print(f"Saved table {i+1} to {csv_output_path}")
        print(f"All extracted tables have been saved to the '{output_dir}' directory.")
    else:
        print("No tables were found in the PDF using 'lattice' flavor. You might try 'stream' flavor if the tables lack clear borders.")

    # Combine all extracted table CSVs into one file.
    csv_files = sorted(
        os.path.join(output_dir, filename)
        for filename in os.listdir(output_dir)
        if filename.lower().endswith('.csv') and filename != 'combined_tables.csv'
    )
    if csv_files:
        combined = pd.concat((pd.read_csv(path) for path in csv_files), ignore_index=True)
        combined.to_csv('combined_tables.csv', index=False, encoding='utf-8')
        print(f"Combined {len(csv_files)} CSV files into combined_tables.csv")
    else:
        print(f"No CSV files found in '{output_dir}' to combine.")

except Exception as e:
    print(f"An error occurred: {e}")
    print("Please ensure the PDF is valid and try adjusting the 'flavor' parameter (e.g., flavor='stream') if tables are not detected.")

