import sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pyxrt
X = r"E:\trixdna_test\phase5_atb\phase5_atb_m32k64n128.xclbin"
d = pyxrt.device(0)
x = pyxrt.xclbin(X)
u = d.register_xclbin(x)
h = pyxrt.hw_context(d, u)
kb = x.get_kernels()[0]
print("xclbinkernel public:", [a for a in dir(kb) if not a.startswith("_")])
print("get_num_args() =", kb.get_num_args())
k = pyxrt.kernel(h, kb.get_name())
print("kernel public:", [a for a in dir(k) if not a.startswith("_")])
for i in range(kb.get_num_args()):
    for meth in ("get_arg",):
        f = getattr(k, meth, None)
        if f:
            try:
                a = f(i)
                print(f"  arg[{i}] name={getattr(a,'name',None)} type={getattr(a,'type',None)} size={getattr(a,'size',None)} dir={[z for z in dir(a) if not z.startswith('_')]}")
            except Exception as e:
                print(f"  arg[{i}] ERREUR {type(e).__name__}: {e}")
print("pyxrt top-level:", [a for a in dir(pyxrt) if not a.startswith("_")][:40])
