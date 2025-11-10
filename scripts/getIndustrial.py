import pandas as pd
import requests
import os
import time

CENSUS_API_KEY = "4991b9654fa08ce00f935525dbfc2fd634b95bf0"

START_YEAR = 2010
END_YEAR = 2022 

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

CBSA_COUNTY_MAPPING = {
    "35620": ["36005", "36047", "36059", "36061", "36081", "36085", "36103", "36119", "36027", "34003", "34013", "34017", "34019", "34023", "34027", "34031", "34035", "34037", "34039", "34041", "34011", "42017", "42077", "42091", "42103", "42109"], 
    "31080": ["06037", "06059"], 
    "16980": ["17031", "17043", "17089", "17097", "17111", "17197", "17063", "17091", "18073", "18089", "18111", "18127", "18091", "55059"], 
    "26420": ["48039", "48201", "48167", "48071", "48339", "48473", "48291", "48481", "48439"], 
    "19100": ["48085", "48113", "48121", "48251", "48397", "48439", "48231", "48097", "48139", "48217", "48257", "48367"], 
    "38060": ["04013", "04007", "04021"], 
    "12060": ["13089", "13135", "13151", "13171", "13247", "13063", "13121", "13297", "13097", "13159", "13223", "13257", "13113", "13217", "13045", "13077", "13233", "13067", "13255", "13053"], 
    "42660": ["53033", "53053", "53061"], 
    "37980": ["42017", "42029", "42045", "42091", "42101", "42071", "34005", "34007", "34015", "34021", "10003", "24015"], 
    "33460": ["27003", "27019", "27025", "27037", "27053", "27059", "27123", "27129", "27139", "27163", "27141", "55009", "55013", "55033", "55093"], 
    "38300": ["42003", "42059", "42061", "42125", "42129", "42007", "42073"], 
    "41740": ["06073"] 
}

VARIABLES_TO_FETCH = ["ESTAB", "NAICS", "GEO_ID"]

TARGET_NAICS = "31-33"

CBSA_NAME_MAP = {v: k for k, v in TARGET_CBSA_MAPPING.items()}
ALL_TARGET_FIPS = set()
for fips_list in CBSA_COUNTY_MAPPING.values():
    ALL_TARGET_FIPS.update(fips_list)

OUTPUT_FILENAME = "industrial_activity_manufacturing_establishments_2010_2022.csv"

def fetch_cbp_data(year, api_key, variables):
    """
    Fetches County Business Patterns data for ALL NAICS sectors in a given year.
    The NAICS filtering will be done in Python/Pandas.
    """
    
    base_url = f"https://api.census.gov/data/{year}/cbp"
    
    params = {
        "get": ",".join(variables),
        "for": "county:*", 
        "in": "state:*",
        "key": api_key
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        df = pd.DataFrame(data[1:], columns=data[0])
        df['Year'] = year
        df['State_County_FIPS'] = df['state'] + df['county']
        
        df.rename(columns={'ESTAB': 'Manufacturing_Establishments', 'NAICS': 'NAICS_Code', 'GEO_ID': 'GEO_ID_Full'}, inplace=True)

        return df
        
    except requests.exceptions.HTTPError as e:
        print(f"  Error fetching CBP data for {year}: HTTP {response.status_code}. Skipping this year.")
        return pd.DataFrame()
    except Exception as e:
        print(f"  An unexpected error occurred for {year}: {e}. Skipping this year.")
        return pd.DataFrame()

if __name__ == "__main__":
    
    all_industrial_data = []
    
    print(f"--- Starting CBP Fetch for {START_YEAR} - {END_YEAR} (Manufacturing Establishments - FINAL ATTEMPT) ---")
    
    for year in range(START_YEAR, END_YEAR + 1):
        print(f"-> Fetching data for {year}...")
        
        df_year = fetch_cbp_data(year, CENSUS_API_KEY, VARIABLES_TO_FETCH)
        
        if not df_year.empty:
            
            df_filtered_naics = df_year[df_year['NAICS_Code'] == TARGET_NAICS].copy()

            if df_filtered_naics.empty:
                print(f"  Warning: No Manufacturing data (NAICS 31-33) found for year {year}. Skipping.")
                time.sleep(0.5)
                continue

            df_final_filter = df_filtered_naics[df_filtered_naics['State_County_FIPS'].isin(ALL_TARGET_FIPS)].copy()

            if df_final_filter.empty:
                print(f"  Warning: No data found for target counties in year {year}.")
                time.sleep(0.5)
                continue
            
            df_final_filter['CBSA_Code'] = ''
            for cbsa_code, fips_list in CBSA_COUNTY_MAPPING.items():
                df_final_filter.loc[df_final_filter['State_County_FIPS'].isin(fips_list), 'CBSA_Code'] = cbsa_code
                
            df_final_filter['Manufacturing_Establishments'] = pd.to_numeric(
                df_final_filter['Manufacturing_Establishments'], errors='coerce'
            ).fillna(0)
            
            df_cbsa = df_final_filter.groupby(['Year', 'CBSA_Code'], as_index=False).agg(
                Manufacturing_Establishments=('Manufacturing_Establishments', 'sum')
            )
            
            df_cbsa['Manufacturing_Establishments'] = df_cbsa['Manufacturing_Establishments'].astype(int)

            # 4. Add CBSA Name
            df_cbsa['CBSA_Name'] = df_cbsa['CBSA_Code'].astype(str).map(CBSA_NAME_MAP)

            all_industrial_data.append(df_cbsa)
            
        time.sleep(0.5)

    if all_industrial_data:
        master_df = pd.concat(all_industrial_data, ignore_index=True)
        
        final_columns = [
            'Year', 'CBSA_Name', 'CBSA_Code', 
            'Manufacturing_Establishments'
        ]
        
        master_df = master_df[final_columns].sort_values(by=['CBSA_Name', 'Year']).reset_index(drop=True)

        master_df.to_csv(OUTPUT_FILENAME, index=False)

        print(f"\n--- Script Complete ---")
        print(f"SUCCESS: Industrial Activity data (Manufacturing Establishments) fetched and calculated.")
        print(f"Final dataset saved to: {OUTPUT_FILENAME}")
        print(f"Total rows in output: {len(master_df)}")
        print("\nFiltered Data Head (First 5 Rows):")
        print(master_df.head())
    else:
        print("\n--- Script Complete ---")
        print("FATAL ERROR: No industrial data was successfully fetched. Please re-check your Census API key and the script's configuration.")
