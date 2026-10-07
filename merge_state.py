"""seen.json-ის გაერთიანება: თუ ორმა გაშვებამ ერთდროულად შეინახა, არცერთის მონაცემი არ იკარგება."""
import json, sys
mine, theirs, out = sys.argv[1:4]
a = json.load(open(mine, encoding="utf-8"))
try:
    b = json.load(open(theirs, encoding="utf-8"))
except Exception:
    b = {}
for k, v in b.items():
    a[k] = list(dict.fromkeys(a.get(k, []) + v))
json.dump(a, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
