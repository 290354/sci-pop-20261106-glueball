"""多进程逐帧渲染：render_at(t) -> jpg"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine
from multiprocessing import Pool

OUT = sys.argv[1] if len(sys.argv) > 1 else "frames"
os.makedirs(OUT, exist_ok=True)

def job(i):
    p = os.path.join(OUT, "f%06d.jpg" % i)
    if os.path.exists(p):
        return 0
    engine.render_at(i / engine.FR).save(p, quality=90)
    return 1

if __name__ == "__main__":
    total = int(round(engine.TOTAL * engine.FR))
    t0 = time.time()
    with Pool(5) as p:
        for k, _ in enumerate(p.imap_unordered(job, range(total), chunksize=40)):
            if k and k % 3000 == 0:
                print(f"{k}/{total} {time.time()-t0:.0f}s", flush=True)
    print("done", total, f"{time.time()-t0:.0f}s")
