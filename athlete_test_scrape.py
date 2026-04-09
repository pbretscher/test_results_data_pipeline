# %%
import pandas as pd
import os
import re
#import pyarrow as pq
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql+psycopg2://postgres:prb9727@localhost:5432/AthleteTestingDB"
)

def get_file_info(relative_path: str) -> str:
    file = os.path.basename(relative_path).replace(".xlsx", '')
    sheets = pd.ExcelFile(path).sheet_names
    print(f'new file started | {file}')
    return file, sheets

def get_df(relative_path: str, camp_name: str, sht: str):
    df = pd.read_excel(relative_path, header=None, sheet_name=sht)
    df = df.dropna(axis=1, how='all')
    print(f'New df collected for {sheet}')
    return df

def append_records(file: str, sht: str, ath:str, f_exe:str, sde:str, ky:str, val:str):
        records.append({
        'file_name': file,
        'sheet': sht,
        'athlete': ath,
        'exercise': f_exe,
        'side': sde,
        'key': ky,
        'value': val
    })

    
if __name__ == '__main__':

    records = []
    #path = '../data/raw/March 2024 NT Camp Testing spread sheet - edited.xlsx'
    #path = '../data/raw/March 2025 NTC Testing.xlsx'
    #path = '../data/raw/March 2026 NTC Testing.xlsx'

    file_name, sheet_list = get_file_info(path)

    for sheet in sheet_list[1:]:
        og_df = get_df(path, file_name, sheet)

        for idx, row in og_df.iterrows():

            if row.isna().all(): # skip row if all blank
                continue
            
            key = str(row.iloc[0].strip().lower()) # clean and get first value in row

            # athlete names row
            if idx == 3:
                athletes = row.iloc[1:].tolist()
                side = key
                continue

            # detect new exercise
            if key and row[1:].isna().all() and key not in ['right', 'left', 'bilateral', 'l single leg squat','r single leg squat', 'pain (n/10)', 'pain', 'pain (er or ir)', 'if pain, where?', 'modified position (y/n)','pain location']:
                exercise = key
                modifier = None  # ✅ reset every row (important)
                continue

            # side detection
            if key in ['right', 'left', 'bilateral']:
                side = key
                continue

            if key in ['isometric mid-thigh pull', 'sit & reach', 'pike leg lifts (n)', "60' sprint", 'timed bounce', 'back tuck', 'vertical jump', 'trunk endurance assessment', 'sorenson', 'jump height (forcedex) inches', 'jump height (imp-mom) in inches']:
                exercise = key
                modifier = None
                side = 'bilateral'

            if key in ['total arc of motion (deg)', 'pain (er or ir)']:
                continue

            if key == 'l single leg squat':
                side = 'left'
            if key == 'r single leg squat':
                side = 'right'
            # force sides for certain exercises
            #if exercise in ['isometric mid-thigh pull', 'trunk endurance assessment', 'sorenson']:
            #    side = 'bilateral'
            
            if exercise in ['left side plank']:
                side = 'left'
            
            if exercise in ['right side plank']:
                side = 'right'



            # key outlier detection
            base_exercise = exercise

            if key in ['knee flexed (°)', 'knee extended (°)',
                        'external rotation (deg)', 'internal rotation (deg)']:
                modifier = key

            # build final exercise
            if modifier:
                final_exercise = f"{base_exercise} - {modifier}"
            else:
                final_exercise = base_exercise

            if row[1] == athletes[0]:
                continue


            # identify values
            for athlete, value in zip(athletes, row.iloc[1:]):
                value = str(value).strip().lower() # get value strip and lower

                # time conversion
                if key in ['time held (min:sec)', 'sorenson']:
                    try:
                        parts = value.split(':')
                        if len(parts) == 2:
                            minutes, seconds = map(int, parts)
                            value = minutes * 60 + seconds
                        elif len(parts) == 3:
                            hours, minutes, seconds = map(int, parts)
                            value = hours * 60 + minutes
                        else:
                            value = None
                    except:
                        value = None

                # skip junk values
                if value in [
                    '-', 'no', '', '0', 'cap', 'n', '?', 'nt', 'x',
                    'nt - injury', 'injury', 'injured', 'nan', None
                ] or pd.isna(value):
                    continue


                # 🔥 FIXED PAIN HANDLING
                if 'pain' in key and 'where' not in key:
                    parts = re.split(r',\s*', value)

                    for part in parts:
                        part = part.strip().lower()

                        # detect ER / IR
                        if 'er' in part:
                            modifier_local = 'external rotation (deg)'
                        elif 'ir' in part:
                            modifier_local = 'internal rotation (deg)'
                        else:
                            modifier_local = None

                        # extract number
                        match = re.search(r'\d+', part)

                        if not match:
                            continue

                        pain_value = int(match.group())

                        # rebuild  proper exerise
                        if modifier_local:
                            final_ex = f"{base_exercise} - {modifier_local}"
                        else:
                            final_ex = base_exercise
                        if 'knee' in last_exercise:
                            final_ex = last_exercise

                        #if 'pain (n/10)' in final_ex:
                            #print(exercise, final_ex, pain_value, athlete, side)

                        append_records(file_name, sheet, athlete, final_ex, side, 'pain', pain_value)


                    continue  # ✅ skip normal append

                append_records(file_name, sheet, athlete, final_exercise, side, key, value)
                
                last_exercise = final_exercise

    cdf = pd.DataFrame(records)

    #cdf.to_csv("../data/processed/raw_stagingcleaned.csv", header=1, index=False)

# %%
    # %%
    cdf = cdf.loc[~cdf['exercise'].isin(['ratios', 'symmetry'])]
    cdf = cdf.loc[~cdf['key'].isin(['% of norm', 'norm strength (lbs)', 'total arc of rom', 'modified position (y/n)'])]
    cdf['exercise'] = cdf['exercise'].replace('trunk endurance assessment', 'prone plank')
    cdf.loc[cdf['key'].str.contains('location', case=False, na=False), 'key'] = 'location'
    cdf.loc[cdf['key'].str.contains('termination', case=False, na=False), 'key'] = 'location'
    cdf.loc[cdf['key'].str.contains('where', case=False, na=False), 'key'] = 'location'
    cdf.loc[cdf['key'].str.contains('pain', case=False, na=False), 'key'] = 'pain'
    cdf.loc[~cdf['key'].str.contains(r'pain|location', case=False, na=False),'key'] = 'value'

# %%
wide = cdf.pivot_table(
    index=['file_name','sheet', 'athlete', 'exercise', 'side'],
    columns="key",
    values="value",
    aggfunc="first"
).reset_index()

wide = wide[pd.to_numeric(wide['value'], errors='coerce').notna()]

# %%
wide['location'] = wide['location'].astype(str)
wide['pain'] = wide['pain'].astype('Int64')
wide['value'] = wide['value'].astype(float)
wide = wide[
    wide['value'].notna() & 
    (wide['value'].astype(str).str.strip() != '') &
    (wide['value'].astype(str).str.lower() != 'nan')
]

wide.columns = [
'file_name',
'sheet',
'athlete',
'exercise',
'side',
'pain_location',
'pain',
'value'
]

# %%
#wide.to_parquet(path='../data/staging/Mar24.parquet', index=False, engine='pyarrow', compression='snappy')
#wide.to_csv("../data/processed/stagingcleanded.csv", header=1, index=False)
wide.to_sql(name='raw_athlete_test', con=engine, schema='bronze', if_exists='append', index=False)





