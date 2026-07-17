import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import openpyxl
from openpyxl.styles import PatternFill, Alignment

def scrape_pasuram_page(url):
    # Add delay to be respectful to the server
    time.sleep(2)
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract pasuram number from URL
        pasuram_num = url.rstrip('/').split('/')[-1]
        
        # Extract the Pasuram text (verse block before பதவுரை table)
        pasuram_text = []
        for p in soup.find_all('p'):
            if 'பதவுரை' in p.get_text():
                break
            # Preserve the text with its original line breaks
            lines = [line.strip() for line in p.get_text().split('\n') if line.strip()]
            pasuram_text.extend(lines)
        
        # Join with newlines to preserve structure and add extra newline for Excel
        pasuram_text = '\n'.join(pasuram_text)
        
        # Find the பதவுரை table
        tables = soup.find_all('table')
        data_rows = []
        padham_counter = 1  # Initialize counter for each Pasuram
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 1:  # Changed to 1 to include merged columns
                    padham = cols[0].get_text(strip=True)
                    
                    has_colspan = any(col.get('colspan') for col in cols)
                    is_merged = len(cols) == 1 or has_colspan

                    if len(cols) >= 3:
                        padham = cols[0].get_text(strip=True)
                        meaning = cols[2].get_text(strip=True)
                        is_merged = False
                    elif len(cols) == 2 and not has_colspan:
                        # Two-column padham | meaning layout (e.g. Thiruvirutham 2535)
                        padham = cols[0].get_text(strip=True)
                        meaning = cols[1].get_text(strip=True)
                        is_merged = False
                    else:
                        meaning = cols[0].get_text(strip=True)
                        padham = "NOTE"
                    
                    if (padham and meaning) or is_merged:  # Include both regular and merged cells
                        data_rows.append({
                            'PasuramNo': pasuram_num,
                            'Pasuram': pasuram_text,
                            'Padham': padham,
                            'Meaning': meaning,
                            'PadhamNo': padham_counter if not is_merged else None,
                            'is_merged': is_merged
                        })
                        if not is_merged:
                            padham_counter += 1
        
        return data_rows
    
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return []

def main():
    # Generate URLs to scrape
    base_url = "https://www.dravidaveda.org/"
    urls = [f"{base_url}{i}/" for i in range(2282, 2382)]  # Changed range to 2181-2182 (1 pasuram)

    # Collect all data
    all_data = []
    for url in urls:
        print(f"Scraping {url}...")
        data_rows = scrape_pasuram_page(url)
        all_data.extend(data_rows)
        
    # Create DataFrame
    df = pd.DataFrame(all_data)
    
    # Reorder columns to match requested format
    df = df[['PasuramNo', 'Pasuram', 'Padham', 'Meaning', 'PadhamNo']]
    
    # Ensure proper encoding for Tamil text and handle line breaks for Excel
    writer = pd.ExcelWriter('mundramthiruvandhathi.xlsx', engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Pasuram Data')
    
    # Get the workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets['Pasuram Data']
    
    # Define fill pattern for merged cells (bright yellow)
    yellow_fill = PatternFill(start_color='FFFF99', end_color='FFFF99', fill_type='solid')
    
    # Format cells
    for idx, row in df.iterrows():
        # Excel row is 1-based and we need to account for header row
        excel_row = idx + 2
        
        # Adjust row height to accommodate multiple lines
        worksheet.row_dimensions[excel_row].height = 60
        
        # Set wrap text for Pasuram column
        pasuram_cell = worksheet.cell(row=excel_row, column=2)  # Column B (Pasuram)
        pasuram_cell.alignment = openpyxl.styles.Alignment(wrap_text=True, vertical='top')
        
        # If this is a merged cell row or has NOTE marker, highlight it
        if row.get('is_merged') or row['Padham'] == 'NOTE':
            for col in range(1, 6):  # Columns A to E
                cell = worksheet.cell(row=excel_row, column=col)
                cell.fill = yellow_fill
                cell.alignment = openpyxl.styles.Alignment(wrap_text=True, vertical='top')
    
    # Adjust column widths
    worksheet.column_dimensions['A'].width = 15  # PasuramNo
    worksheet.column_dimensions['B'].width = 50  # Pasuram
    worksheet.column_dimensions['C'].width = 30  # Padham
    worksheet.column_dimensions['D'].width = 50  # Meaning
    worksheet.column_dimensions['E'].width = 15  # PadhamNo
    
    # Save the file
    writer.close()

    print(f"Successfully scraped {len(urls)} pages and saved data to rendamthiruvandhathi.xlsx")

if __name__ == "__main__":
    main()
