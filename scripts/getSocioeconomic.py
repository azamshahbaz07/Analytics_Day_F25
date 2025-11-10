import pandas as pd
import requests
import os
import time

# --- 1. CONFIGURATION ---

CENSUS_API_KEY = "4991b9654fa08ce00f935525dbfc2fd634b95bf0"

# Target Years: ACS 1-Year data runs from 2010 up to the most recent release (typically 2023)
START_YEAR = 2010
END_YEAR = 2023

# Target CBSA Codes (Mapped from your 12 city names)
TARGET_CBSA_MAPPING = {
    "New York-Newark-Jersey City, NY-NJ-PA": "35620",
    "Los Angeles-Long Beach-Anaheim, CA": "31080",
    "Chicago-Naperville-Elgin, IL-IN-WI": "16980",
    "Houston-The Woodlands-Sugar Land, TX": "26420",
    "Dallas-Fort Worth-Arlington, TX": "19100",
    "Phoenix-Mesa-Scottsdale, AZ": "38060",
    "Atlanta-Sandy Springs-Roswell, GA": "12060",
    "Seattle-Tacoma-Bellevue, WA": "42660",
    "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD": "37980",
    "Minneapolis-St. Paul-Bloomington, MN-WI": "33460",
    "Pittsburgh, PA": "38300",
    "San Diego-Carlsbad, CA": "41740"
}

# Source: U.S. Census Bureau 2020 Land Area (sq mi) for the 12 CBSAs.
CBSA_LAND_AREA_SQMI = {
    "35620": 13374.80, # New York-Newark-Jersey City
    "31080": 4850.70,  # Los Angeles-Long Beach-Anaheim
    "16980": 8573.40,  # Chicago-Naperville-Elgin
    "26420": 10062.60, # Houston-The Woodlands-Sugar Land
    "19100": 9279.70,  # Dallas-Fort Worth-Arlington
    "38060": 14594.10, # Phoenix-Mesa-Scottsdale
    "12060": 8376.10,  # Atlanta-Sandy Springs-Roswell
    "42660": 6393.80,  # Seattle-Tacoma-Bellevue
    "37980": 5831.60,  # Philadelphia-Camden-Wilmington
    "33460": 7919.10,  # Minneapolis-St. Paul-Bloomington
    "38300": 5440.00,  # Pittsburgh
    "41740": 4205.50   # San Diego-Carlsbad
}

# Variables to fetch from the DETAILED endpoint (All B-tables)
VARIABLES_TO_FETCH = [
    "NAME",
    "B01003_001E",      # Total Population
    "B19013_001E",      # Median Household Income
    # Poverty Rate components
    "B17010_001E",      # Total Families (Denominator for poverty)
    "B17010_002E",      # Families Below Poverty (Numerator for poverty)
    # Education components (Population 25 years and over)
    "B15003_001E",      # Total Pop 25+ (Denominator for education)
    "B15003_017E",      # High School Graduate (component of HS+)
    "B15003_018E",      # Some college, no degree (component of HS+)
    "B15003_019E",      # Associate's degree (component of HS+)
    "B15003_020E",      # Bachelor's degree (component of HS+)
    "B15003_021E",      # Master's degree (component of HS+)
    "B15003_022E",      # Professional school degree (component of HS+)
    "B15003_023E",      # Doctorate degree (component of HS+)
    # Labor Force components (Population 16 years and over)
    "B23001_003E",      # Civilian Labor Force
    "B23001_002E",      # Total Population 16+ in Labor Force (Denominator for participation rate)
    "B23001_008E"       # Unemployed
]

# Rename map for clarity
COLUMN_RENAME_MAP = {
    'B01003_001E': 'Total_Population',
    'B19013_001E': 'Median_Household_Income_USD',
    'B17010_001E': 'Poverty_Total_Families',
    'B17010_002E': 'Poverty_Families_Below',
    'B15003_001E': 'Education_Pop_25_Plus',
    'B15003_017E': 'Ed_HS_Grad',
    'B15003_018E': 'Ed_Some_College',
    'B15003_019E': 'Ed_Associates',
    'B15003_020E': 'Ed_Bachelors',
    'B15003_021E': 'Ed_Masters',
    'B15003_022E': 'Ed_Professional',
    'B15003_023E': 'Ed_Doctorate',
    'B23001_003E': 'Labor_Civilian_Labor_Force',
    'B23001_002E': 'Labor_Total_In_Labor_Force',
    'B23001_008E': 'Labor_Unemployed',
    'metropolitan statistical area/micropolitan statistical area': 'CBSA_Code'
}

OUTPUT_FILENAME = "socioeconomic.csv"

# --- 2. API CALL FUNCTION ---

def fetch_census_data(year, cbsa_codes, api_key, variables):
    """Fetches data using the stable /acs/acs1 endpoint."""
    
    # Using the standard /acs/acs1 endpoint for all B-tables
    base_url = f"https://api.census.gov/data/{year}/acs/acs1"
    geography = ",".join(cbsa_codes)
    
    params = {
        "get": ",".join(variables),
        "for": f"metropolitan statistical area/micropolitan statistical area:{geography}",
        "key": api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        df = pd.DataFrame(data[1:], columns=data[0])
        df['Year'] = year
        
        df.rename(columns=COLUMN_RENAME_MAP, inplace=True)
        df.drop(columns=['state', 'county'], errors='ignore', inplace=True)

        return df
        
    except requests.exceptions.HTTPError as e:
        print(f"  Error fetching data for {year}: HTTP {response.status_code}. Skipping this year.")
        return pd.DataFrame()
    except Exception as e:
        print(f"  An unexpected error occurred for {year}: {e}. Skipping this year.")
        return pd.DataFrame()

# --- 3. MAIN EXECUTION ---

if __name__ == "__main__":
    
    all_socioeconomic_data = []
    cbsa_codes = list(TARGET_CBSA_MAPPING.values())
    
    print(f"--- Starting Census API Fetch for {START_YEAR} - {END_YEAR} (FINAL ATTEMPT) ---")
    
    for year in range(START_YEAR, END_YEAR + 1):
        print(f"-> Fetching data for {year}...")
        
        df_year = fetch_census_data(year, cbsa_codes, CENSUS_API_KEY, VARIABLES_TO_FETCH)
        
        if not df_year.empty:
            # Add the official CBSA Name back using the mapping
            name_map = {code: name for name, code in TARGET_CBSA_MAPPING.items()}
            df_year['CBSA_Name'] = df_year['CBSA_Code'].astype(str).map(name_map)
            all_socioeconomic_data.append(df_year)
            
        time.sleep(0.5) # API courtesy

    # Concatenate all annual data
    if all_socioeconomic_data:
        master_df = pd.concat(all_socioeconomic_data, ignore_index=True)
        
        # Convert all relevant count columns to numeric
        raw_count_cols = [
            col for col in master_df.columns 
            if col not in ['Year', 'CBSA_Name', 'CBSA_Code', 'NAME', 'Median_Household_Income_USD']
        ]
        for col in raw_count_cols:
             # Use errors='coerce' to turn any non-numeric Census codes (like '(X)') into NaN
             master_df[col] = pd.to_numeric(master_df[col], errors='coerce')

        # --- 4. CALCULATE DERIVED VARIABLES ---
        
        # 1. Population Density
        area_map = {code: area for code, area in CBSA_LAND_AREA_SQMI.items()}
        master_df['CBSA_Land_Area_SqMi'] = master_df['CBSA_Code'].astype(str).map(area_map)
        master_df['Population_Density'] = master_df['Total_Population'] / master_df['CBSA_Land_Area_SqMi']
        
        # 2. Poverty Rate: (Families Below Poverty / Total Families) * 100
        master_df['Poverty_Rate_Pct'] = (
            master_df['Poverty_Families_Below'] / master_df['Poverty_Total_Families']
        ) * 100
        
        # 3. Education Levels (HS & Bachelor's)
        # Calculate Pop 25+ with HS Degree or higher
        master_df['Education_HS_Degree_Plus_Count'] = (
            master_df['Ed_HS_Grad'] + master_df['Ed_Some_College'] + 
            master_df['Ed_Associates'] + master_df['Ed_Bachelors'] + 
            master_df['Ed_Masters'] + master_df['Ed_Professional'] + 
            master_df['Ed_Doctorate']
        )
        master_df['Education_HS_Degree_Plus_Pct'] = (
            master_df['Education_HS_Degree_Plus_Count'] / master_df['Education_Pop_25_Plus']
        ) * 100

        # Calculate Pop 25+ with Bachelor's Degree or higher
        master_df['Education_Bachelors_Degree_Plus_Count'] = (
            master_df['Ed_Bachelors'] + master_df['Ed_Masters'] + 
            master_df['Ed_Professional'] + master_df['Ed_Doctorate']
        )
        master_df['Education_Bachelors_Degree_Plus_Pct'] = (
            master_df['Education_Bachelors_Degree_Plus_Count'] / master_df['Education_Pop_25_Plus']
        ) * 100

        # 4. Labor Force Participation / Unemployment
        # Labor Force Participation Rate: (Civilian Labor Force / Total Population 16+ in Labor Force) * 100
        master_df['Labor_Force_Participation_Rate_Pct'] = (
            master_df['Labor_Civilian_Labor_Force'] / master_df['Labor_Total_In_Labor_Force']
        ) * 100
        
        # Unemployment Rate: (Unemployed / Civilian Labor Force) * 100
        master_df['Unemployment_Rate_Pct'] = (
            master_df['Labor_Unemployed'] / master_df['Labor_Civilian_Labor_Force']
        ) * 100
        
        # --- 5. Final Column Selection and Save ---
        
        final_columns = [
            'Year', 'CBSA_Name', 'CBSA_Code', 
            'Total_Population', 'Population_Density',
            'Median_Household_Income_USD', 'Poverty_Rate_Pct',
            'Education_HS_Degree_Plus_Pct', 'Education_Bachelors_Degree_Plus_Pct',
            'Labor_Force_Participation_Rate_Pct', 'Unemployment_Rate_Pct'
        ]
        
        master_df = master_df[final_columns].sort_values(by=['CBSA_Name', 'Year']).reset_index(drop=True)

        # Save the final result
        master_df.to_csv(OUTPUT_FILENAME, index=False)

        print(f"\n--- Script Complete ---")
        print(f"SUCCESS: All 7 socioeconomic variables were successfully fetched and calculated.")
        print(f"Final socioeconomic dataset saved to: {OUTPUT_FILENAME}")
        print(f"Total rows in output: {len(master_df)}")
        print("\nFiltered Data Head (First 5 Rows):")
        print(master_df.head())
    else:
        print("\n--- Script Complete ---")
        print("FATAL ERROR: No socioeconomic data was successfully fetched after multiple attempts. Please re-check your Census API key validity.")
