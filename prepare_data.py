import io
import sys
import urllib.error
import urllib.request
import zipfile

import pandas as pd

URL = "https://openpsychometrics.org/_rawdata/IPIP-FFM-data-8Nov2018.zip"
OUTPUT_PATH = "spike_data.csv"
EXT_COLUMNS = [f"EXT{i}" for i in range(1, 11)]
SAMPLE_SIZE = 1000


class PreparationError(Exception):
    """Felismert, felhasználónak szóló adat-előkészítési hiba."""


def prepare() -> None:
    print("Letöltés az OpenPsychometrics szerveréről (ez eltarthat 1-2 percig)...")

    # Letöltés és kicsomagolás a memóriában
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as z:
            # Megkeressük a CSV fájlt a zipen belül
            tables = [name for name in z.namelist() if name.endswith('.csv') or name.endswith('.tsv')]
            if not tables:
                raise PreparationError("A letöltött ZIP nem tartalmaz .csv vagy .tsv fájlt.")
            csv_filename = tables[0]
            print(f"Fájl megtalálva: {csv_filename}. Adatok feldolgozása...")

            with z.open(csv_filename) as f:
                # Az IPIP-FFM adatbázis általában tabulátorral van elválasztva
                df = pd.read_csv(f, sep='\t', low_memory=False)

    # 1. Lépés: Kiválasztunk egyetlen 10 kérdéses blokkot (EXT1 - EXT10)
    missing = [column for column in EXT_COLUMNS if column not in df.columns]
    if missing:
        raise PreparationError(f"Hiányzó oszlopok az adatfájlban: {', '.join(missing)}")

    # 2. Lépés: Kivágunk 1000 sort, amiben nincs hiányzó adat (NaN)
    complete = df[EXT_COLUMNS].dropna()
    if len(complete) < SAMPLE_SIZE:
        raise PreparationError(
            f"Csak {len(complete)} teljes sor érhető el, legalább {SAMPLE_SIZE} szükséges."
        )
    df_sample = complete.head(SAMPLE_SIZE)

    # 3. Lépés: Elmentjük a fájlt (utolsó lépés, így hiba esetén a régi fájl érintetlen marad)
    df_sample.to_csv(OUTPUT_PATH, index=False)
    print(f"Siker! A '{OUTPUT_PATH}' fájl ({SAMPLE_SIZE} sor, {len(EXT_COLUMNS)} oszlop) létrejött a mappádban.")


def main() -> int:
    try:
        prepare()
    except (urllib.error.URLError, zipfile.BadZipFile, OSError, pd.errors.ParserError, PreparationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
