# Install required libraries first
print("Installing camelot-py and Ghostscript...")
!pip install camelot-py[cv] > /dev/null
!apt-get install ghostscript -y > /dev/null
print("Installation complete.")

import os
import camelot

# Define the PDF file path
pdf_file_path = '/content/115年存匯內部證照第二次檢定題庫(本題庫部份內容、選項出題時會稍作變化，請同仁熟讀!)115 07 15.pdf'

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

except Exception as e:
    print(f"An error occurred: {e}")
    print("Please ensure the PDF is valid and try adjusting the 'flavor' parameter (e.g., flavor='stream') if tables are not detected.")

import pandas as pd
import os

# Directory where CSV files are saved
output_dir = 'extracted_tables'

# List all CSV files in the directory
csv_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.csv')]

# Check if any CSV files were found
if not csv_files:
    print(f"No CSV files found in the directory: {output_dir}")
else:
    print(f"Found {len(csv_files)} CSV files. Merging them into a single file...")
    
    # Read each CSV file into a DataFrame and store them in a list
    all_dataframes = []
    for csv_file in sorted(csv_files): # Sort for consistent order
        try:
            df = pd.read_csv(csv_file)
            all_dataframes.append(df)
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")

    # Concatenate all DataFrames into a single DataFrame
    if all_dataframes:
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        
        # Define the path for the combined CSV file
        combined_csv_path = 'combined_tables.csv'
        
        # Save the combined DataFrame to a new CSV file
        combined_df.to_csv(combined_csv_path, index=False, encoding='utf-8')
        print(f"Successfully merged all CSV files into {combined_csv_path}")
        print("First 5 rows of the combined CSV:")
        display(combined_df.head())
    else:
        print("No dataframes were successfully read to combine.")