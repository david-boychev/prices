"""
Downloads the GSM Shop price list CSV, adds a markup, and builds index.html.
Run:  pip install requests   then   python build.py
Source page: https://www.gsmbox.at/de/  (Price lists -> Mobile phones, tablets, wearables & gadgets)
"""
import re, csv, io, html, json, datetime
import requests

CSV_URL = "https://pricelist.gsmshop.at/mobil_en_new.csv"
MARKUP = 1.06          # +6 %
OUTPUT = "index.html"

STAMP = re.compile(r"Time Stamp:\s*([\d.]+\s+[\d:]+)")


def fetch_rows():
    resp = requests.get(CSV_URL, timeout=60)
    resp.raise_for_status()
    text = resp.content.decode("utf-8-sig", errors="replace")
    rows, stamp = [], ""
    for line in csv.reader(io.StringIO(text), delimiter=";"):
        if not line:
            continue
        if not stamp and (m := STAMP.search(line[0])):
            stamp = m.group(1)
        # data rows: ID;Item;QTY;Incoming;Price Euro;
        if len(line) < 5 or not line[0].strip().isdigit():
            continue
        try:
            cost = float(line[4].strip().replace(".", "").replace(",", "."))
            stock, incoming = int(line[2]), int(line[3])
        except ValueError:
            continue
        rows.append({
            "name": line[1].strip(),
            "art": line[0].strip(),
            "stock": max(stock, 0),
            "incoming": incoming,
            "price": round(cost * MARKUP, 2),
            "tag": "",
        })
    return rows, stamp


def build_page(rows, stamp):
    data = json.dumps(rows, ensure_ascii=False)
    built = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Price List</title>
<style>
:root{{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#e5e5e5;--head:#f6f6f6;--accent:#0a66c2}}
@media (prefers-color-scheme:dark){{:root{{--bg:#121212;--fg:#eee;--muted:#999;--line:#2a2a2a;--head:#1c1c1c;--accent:#5aa9ff}}}}
body{{margin:0;font-family:system-ui,sans-serif;background:var(--bg);color:var(--fg)}}
header{{padding:16px;border-bottom:1px solid var(--line)}}
h1{{margin:0 0 4px;font-size:1.4rem}} .meta{{color:var(--muted);font-size:.85rem}}
.bar{{display:flex;gap:8px;flex-wrap:wrap;padding:12px 16px}}
input,select{{padding:8px;font-size:1rem;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}}
input{{flex:1;min-width:200px}}
.wrap{{overflow-x:auto;padding:0 16px 24px}}
table{{width:100%;border-collapse:collapse;font-size:.92rem}}
th,td{{padding:8px;border-bottom:1px solid var(--line);text-align:left}}
th{{background:var(--head);position:sticky;top:0;cursor:pointer}}
td.n,th.n{{text-align:right;white-space:nowrap}}
.tag{{font-size:.7rem;padding:2px 6px;border-radius:4px;background:var(--accent);color:#fff;margin-left:6px}}
.out{{color:var(--muted)}}
</style></head><body>
<header><h1>Price List</h1>
<div class="meta">Source updated: {html.escape(stamp)} · Page built: {built} · Prices in EUR, excl. VAT</div></header>
<div class="bar">
<input id="q" placeholder="Search product or Art.No…">
<select id="brand"><option value="">All brands</option></select>
<label style="align-self:center"><input type="checkbox" id="instock" style="min-width:0;flex:0"> In stock only</label>
</div>
<div class="wrap"><table><thead><tr>
<th data-k="name">Product</th><th data-k="art">Art.No</th><th class="n" data-k="stock">Stock</th>
<th class="n" data-k="incoming">Incoming</th><th class="n" data-k="price">Price €</th>
</tr></thead><tbody id="tb"></tbody></table></div>
<script>
const rows={data};
const tb=document.getElementById('tb'),q=document.getElementById('q'),
      br=document.getElementById('brand'),st=document.getElementById('instock');
[...new Set(rows.map(r=>r.name.split(' ')[0]))].sort((a,b)=>a.localeCompare(b,undefined,{{sensitivity:'base'}}))
  .forEach(b=>br.add(new Option(b,b)));
let sortK='name',dir=1;
const fmt=n=>n.toLocaleString('de-DE',{{minimumFractionDigits:2,maximumFractionDigits:2}});
const esc=s=>s.replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
function render(){{
  const t=q.value.toLowerCase().trim(),b=br.value;
  const list=rows.filter(r=>(!t||r.name.toLowerCase().includes(t)||r.art.includes(t))
    &&(!b||r.name.split(' ')[0]===b)&&(!st.checked||r.stock>0))
    .sort((a,c)=>(a[sortK]>c[sortK]?1:a[sortK]<c[sortK]?-1:0)*dir);
  tb.innerHTML=list.map(r=>`<tr class="${{r.stock>0?'':'out'}}"><td>${{esc(r.name)}}${{r.tag?`<span class="tag">${{r.tag}}</span>`:''}}</td>
  <td>${{r.art}}</td><td class="n">${{r.stock}}</td><td class="n">${{r.incoming}}</td><td class="n"><b>${{fmt(r.price)}}</b></td></tr>`).join('');
}}
document.querySelectorAll('th').forEach(th=>th.onclick=()=>{{const k=th.dataset.k;dir=sortK===k?-dir:1;sortK=k;render();}});
[q,br,st].forEach(e=>e.addEventListener('input',render));
render();
</script></body></html>"""


if __name__ == "__main__":
    rows, stamp = fetch_rows()
    if len(rows) < 50:
        raise SystemExit(f"Only {len(rows)} rows parsed - PDF format may have changed, not overwriting.")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(build_page(rows, stamp))
    print(f"Built {OUTPUT}: {len(rows)} products, source time {stamp}")
