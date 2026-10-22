"""Merge concurrent cloud price updates without dropping dated local history."""
import csv
import io
import json
import subprocess
from pathlib import Path
import build

ROOT = Path(__file__).resolve().parent
HTML = {"index.html", "dashboard.html", "★Commodity_dashboard.html"}

def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, text=True, encoding="utf-8",
                          capture_output=True, check=check)

def parse(text):
    reader=csv.DictReader(io.StringIO(text))
    fields=reader.fieldnames or []
    keys=["date","product"] if "product" in fields else ["date"]
    rows={tuple(row[k] for k in keys):row for row in reader}
    return fields,rows

def merge_prices(base_text, local_text, remote_text):
    bf,b=parse(base_text); lf,l=parse(local_text); rf,r=parse(remote_text)
    if lf and rf and lf!=rf:
        raise ValueError("CSV columns differ; manual review required")
    fields=lf or rf
    merged=dict(r)
    for key,row in l.items():
        # A remote correction wins only when this local row is unchanged.
        if key not in r or row != b.get(key):
            merged[key]=row
    out=io.StringIO(newline="")
    writer=csv.DictWriter(out,fieldnames=fields,lineterminator="\n")
    writer.writeheader()
    writer.writerows(merged[k] for k in sorted(merged))
    return out.getvalue()

def main():
    if git("merge-base","--is-ancestor","origin/main","HEAD",check=False).returncode==0:
        return
    if git("status","--porcelain","--untracked-files=no").stdout.strip():
        raise RuntimeError("Commit local changes before synchronization")
    base=git("merge-base","HEAD","origin/main").stdout.strip()
    changed=git("diff","--name-only",base,"origin/main").stdout.splitlines()
    # NUL-separated paths prevent Git quoting non-ASCII filenames.
    changed=git("diff","--name-only","-z",base,"origin/main").stdout.split("\0")
    changed=[n for n in changed if n]
    allowed=lambda n:n in HTML or n=="data/update_status.json" or (n.startswith("data/") and n.endswith(".csv") and "/" not in n[5:])
    if any(not allowed(n) for n in changed):
        git("merge","--no-edit","origin/main")
        return
    contents={}
    def show(ref,n):
        p=git("show",ref+":"+n,check=False)
        return p.stdout if p.returncode==0 else ""
    for name in changed:
        if name.endswith(".csv"):
            contents[name]=merge_prices(show(base,name),show("HEAD",name),show("origin/main",name))
    # Remote changes are generated files only; reconcile every CSV before committing.
    git("merge","--no-commit","--no-ff","-s","ours","origin/main")
    for name,text in contents.items():
        path=ROOT/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding="utf-8")
    build.build()
    git("add","--","data/*.csv",*sorted(HTML))
    git("commit","-m","Merge cloud price history and rebuild local dashboard")
    print("Merged cloud prices; preserved local changes and source dates.")

if __name__=="__main__":
    main()
