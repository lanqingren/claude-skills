#!/usr/bin/env python3
"""Parallel task runner for paper pipeline."""
import subprocess, sys, os, time, argparse, threading

SKILL_BASE = os.path.expandvars(r"%APPDATA%\cn.org.hermesagent.desktop\runtime\hermes-home\skills")

def run_one(name, cmd, timeout):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        ok = r.returncode == 0
        elapsed = time.time() - t0
        print("  [%s] %s: %.1fs" % ("OK" if ok else "FAIL", name, elapsed))
        return {"name": name, "ok": ok, "time": elapsed}
    except:
        print("  [ERR] %s" % name)
        return {"name": name, "ok": False, "time": 0}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--docx", required=True)
    p.add_argument("--figures", default=None)
    p.add_argument("--tasks", default="aigc,review")
    args = p.parse_args()

    diagnose = os.path.join(SKILL_BASE, "aigc-humanize", "scripts", "diagnose.py")
    review = os.path.join(SKILL_BASE, "academic-pre-review-committee", "scripts", "pre_review.py")
    
    txt = args.docx.replace(".docx", "_text.txt")
    # Extract text
    os.system('python -c "from docx import Document; d=Document(r\'%s\'); open(r\'%s\',\'w\',encoding=\'utf-8\').write(\'\\n\'.join([p.text for p in d.paragraphs if p.text.strip()]))"' % (args.docx, txt))

    tasks = []
    if "aigc" in args.tasks:
        tasks.append(("AIGC-CNKI", 'python "%s" --input "%s" --tool cnki' % (diagnose, txt)))
        tasks.append(("AIGC-PP", 'python "%s" --input "%s" --tool paperpass' % (diagnose, txt)))
    if "review" in args.tasks:
        tasks.append(("Review", 'python "%s" --input "%s" --mode quick' % (review, args.docx)))
    if "charts" in args.tasks and args.figures:
        tasks.append(("Charts", 'python "%s"' % args.figures))

    print("Running %d tasks in parallel..." % len(tasks))
    t0 = time.time()
    results = []
    threads = []
    for name, cmd in tasks:
        t = threading.Thread(target=lambda n,c: results.append(run_one(n,c,120)), args=(name,cmd))
        threads.append(t); t.start()
    for t in threads: t.join()
    total = time.time() - t0
    
    ok = sum(1 for r in results if r["ok"])
    serial = sum(r["time"] for r in results)
    print("Done: %d/%d OK, %.1fs (saved %.0fs vs serial %.0fs)" % (ok, len(results), total, serial-total, serial))

if __name__ == "__main__":
    main()
