import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
os.makedirs("qa", exist_ok=True)
for t in [float(x) for x in sys.argv[1:]]:
    E.render_at(t).save(f"qa/s_{int(t*10):04d}.png")
print("ok")
