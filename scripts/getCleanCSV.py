import pandas as pd
import os

data_directory = '/Users/azams/analyticsDayF25/data/dependent'

COLUMNS_TO_KEEP = [
    'Year', 'State Code', 'County Code', 'Site Num', 'POC',
    'Parameter Code', 'Parameter Name', 'Sample Duration', 'Units of Measure',
    'Latitude', 'Longitude', 'State Name', 'County Name', 'CBSA Name',
    'Arithmetic Mean', 'Arithmetic Standard Dev',
    '1st Max Value',
    'Primary Exceedance Count', 'Observation Percent',
    'Valid Day Count', 'Required Day Count',
    '50th Percentile', '90th Percentile', '95th Percentile',
    '98th Percentile', '99th Percentile'
]

TARGET_CBSAS = [
    'New York-Newark-Jersey City, NY-NJ-PA',
    'Los Angeles-Long Beach-Anaheim, CA',
    'Chicago-Naperville-Elgin, IL-IN-WI',
    'Houston-The Woodlands-Sugar Land, TX',
    'Dallas-Fort Worth-Arlington, TX',
    'Phoenix-Mesa-Scottsdale, AZ',
    'Atlanta-Sandy Springs-Roswell, GA',
    'Seattle-Tacoma-Bellevue, WA',
    'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD',
    'Minneapolis-St. Paul-Bloomington, MN-WI',
    'Pittsburgh, PA',
    'San Diego-Carlsbad, CA'
]

start_year = 2010
end_year = 2025
output_filename = "filtered_master_annual_air_quality_12_cities.csv"

def process_annual_summary_file(file_path):
    """
    Reads an EPA annual concentration summary file, selects columns, 
    creates a Site_ID, and returns the processed DataFrame.
    """
    if not os.path.exists(file_path):
        return pd.DataFrame()

    try:
        df = pd.read_csv(file_path)

        available_cols = [col for col in COLUMNS_TO_KEEP if col in df.columns]
        df_processed = df[available_cols].copy()

        df_processed['Site_ID'] = (
            df_processed['State Code'].astype(str).str.zfill(2) + '-' +
            df_processed['County Code'].astype(str).str.zfill(3) + '-' +
            df_processed['Site Num'].astype(str).str.zfill(4) + '-' +
            df_processed['POC'].astype(str).str.zfill(2)
        )

        return df_processed

    except Exception as e:
        print(f"ERROR: Failed to process file {file_path}. Reason: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    
    all_files_to_check = [f"annual_conc_by_monitor_{year}.csv" for year in range(start_year, end_year + 1)]
    all_data = []
    processed_files_count = 0

    print(f"--- Starting Data Processing ({start_year}-{end_year}) ---")
    print(f"Looking for files in directory: {os.path.abspath(data_directory)}\n")


    for file_name in all_files_to_check:
        full_file_path = os.path.join(data_directory, file_name)
        
        if os.path.exists(full_file_path):
            print(f"-> Processing {file_name}...")
            df_processed = process_annual_summary_file(full_file_path)
            if not df_processed.empty:
                all_data.append(df_processed)
                processed_files_count += 1
        else:
            print(f"-> Skipped {file_name}: File not found at path.")

    if all_data:
        master_df = pd.concat(all_data, ignore_index=True)
        
        print("\n-> Filtering data to the 12 target metropolitan areas...")
        filtered_df = master_df[master_df['CBSA Name'].isin(TARGET_CBSAS)].copy()

        output_path = os.path.join(data_directory, output_filename)
        filtered_df.to_csv(output_path, index=False)

        print(f"\n--- Processing Complete ---")
        print(f"Files successfully processed: {processed_files_count}")
        print(f"Total records in the final dataset: {len(filtered_df)}")
        print(f"Final filtered dataset saved to: {output_path}")
        
    else:
        print("\n--- Processing Complete ---")
        print("No files were successfully processed. Check your directory path and file names.")
