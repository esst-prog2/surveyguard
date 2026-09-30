import pandas as pd
import urllib.request
import zipfile
import io
import os

print("Letöltés az OpenPsychometrics szerveréről (ez eltarthat 1-2 percig)...")
url = "https://openpsychometrics.org/_rawdata/IPIP-FFM-data-8Nov2018.zip"

try:
    # Letöltés és kicsomagolás a memóriában
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as z:
            # Megkeressük a CSV fájlt a zipen belül
            csv_filename = [name for name in z.namelist() if name.endswith('.csv') or name.endswith('.tsv')][0]
            print(f"Fájl megtalálva: {csv_filename}. Adatok feldolgozása...")
            
            with z.open(csv_filename) as f:
                # Az IPIP-FFM adatbázis általában tabulátorral van elválasztva
                df = pd.read_csv(f, sep='\t', low_memory=False)
                
    # 1. Lépés: Kiválasztunk egyetlen 10 kérdéses blokkot (EXT1 - EXT10)
    ext_columns = [f"EXT{i}" for i in range(1, 11)]
    
    # 2. Lépés: Kivágunk 1000 sort, amiben nincs hiányzó adat (NaN)
    df_sample = df[ext_columns].dropna().head(1000)
    
    # 3. Lépés: Elmentjük a fájlt
    df_sample.to_csv('spike_data.csv', index=False)
    print("Siker! A 'spike_data.csv' fájl (1000 sor, 10 oszlop) létrejött a mappádban.")

except Exception as e:
    print(f"Hiba történt a letöltés során: {e}")