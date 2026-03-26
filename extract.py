# %%
import pandas as pd
import os
import re
from sqlalchemy import create_engine

# %%
# Get data
engine = create_engine('postgresql+psycopg2://postgres:prb9727@localhost:5432/AthleteTestingDB')
path = '../data/raw/March 2024 NT Camp Testing spread sheet - edited.xlsx'
camp_name = os.path.basename(path).replace(".xlsx", '')
sheets = pd.ExcelFile(path).sheet_names


# %%
records = []

for sheet in sheets[1:]:
    df = pd.read_excel(path, header=None, sheet_name=sheet)
    df = df.dropna(axis=1, how='all')

    for idx, row in df.iterrows():
        modifier = None  # ✅ reset every row (important)
        if row.isna().all():
            continue

        key = str(row.iloc[0]).strip().lower()

        # detect new exercise
        if key and row[1:].isna().all() and key not in ['right', 'left', 'bilateral']:
            exercise = key
            continue

        if key == 'isometric mid-thigh pull':
            exercise = key

        # athlete names row
        if idx == 3:
            athletes = row.iloc[1:].tolist()
            side = key
            continue

        # side detection
        if key in ['right', 'left', 'bilateral']:
            side = key
            continue

        if key == 'total arc of motion (deg)':
            continue

        # force sides for certain exercises
        if exercise in ['isometric mid-thigh pull', 'trunk endurance assessment', 'sorenson']:
            side = 'bilateral'
        
        if exercise == 'left side plank':
            side = 'left'
        
        if exercise == 'right side plank':
            side = 'right'

        base_exercise = exercise

        # modifier detection
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

        for athlete, value in zip(athletes, row.iloc[1:]):
            value = str(value).strip().lower()


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
                'nt - injury', 'injury', 'injured', None
            ] or pd.isna(value):
                continue

            # 🔥 FIXED PAIN HANDLING
            if 'pain' in key:
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

                    # build correct exercise
                    if modifier_local:
                        final_ex = f"{base_exercise} - {modifier_local}"
                    else:
                        final_ex = base_exercise

                    records.append({
                        'file': camp_name,
                        'sheet': sheet,
                        'athlete': athlete,
                        'exercise': final_ex,
                        'side': side,
                        'key': 'pain',
                        'value': pain_value
                    })

                continue  # ✅ skip normal append

            # normal case
            records.append({
                'file': camp_name,
                'sheet': sheet,
                'athlete': athlete,
                'exercise': final_exercise,
                'side': side,
                'key': key,
                'value': value
            })
cdf = pd.DataFrame(records)
cdf.to_csv("../data/processed/raw_mar24cleaned.csv", header=1, index=False)

# %%
cdf = cdf.loc[~cdf['exercise'].isin(['ratios', 'symmetry'])]
cdf = cdf.loc[~cdf['key'].isin(['% of norm', 'norm strength (lbs)', 'total arc of rom', 'modified position (y/n)'])]
cdf['exercise'] = cdf['exercise'].replace('trunk endurance assessment', 'prone plank')
cdf.loc[cdf['key'].str.contains('location', case=False, na=False), 'key'] = 'location'
cdf.loc[cdf['key'].str.contains('pain', case=False, na=False), 'key'] = 'pain'
cdf.loc[~cdf['key'].str.contains(r'pain|location', case=False, na=False),'key'] = 'value'


# %%
wide = cdf.pivot_table(
    index=['file','sheet', 'athlete', 'exercise', 'side'],
    columns="key",
    values="value",
    aggfunc="first"
).reset_index()

# %%
wide['location'] = wide['location'].astype(str)
wide['pain'] = wide['pain'].astype('Int64')
wide['value'] = wide['value'].astype(float)

# %%
wide.to_csv("../data/processed/mar24cleaned.csv", header=1, index=False)
#wide.to_sql(name='athlete_testing_raw', con=engine, schema='bronze', if_exists='replace', index=False)
wide['exercise'].value_counts()


