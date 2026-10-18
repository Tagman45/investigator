import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pyxrt
X = r"E:\trixdna_test\phase5_atb\phase5_atb_m32k64n128.xclbin"
d = pyxrt.device(0); x = pyxrt.xclbin(X); u = d.register_xclbin(x); h = pyxrt.hw_context(d, u)
kb = x.get_kernels()[0]; k = pyxrt.kernel(h, kb.get_name())
print("kernel.group_id par arg:")
for i in range(kb.get_num_args()):
    try:
        print(f"  arg[{i}] group_id={k.group_id(i)}")
    except Exception as e:
        print(f"  arg[{i}] ERREUR {type(e).__name__}: {e}")
print("pyxrt.info public:", [a for a in dir(pyxrt.info) if not a.startswith('_')])
for cls in ("kernel", "device"):
    c = getattr(pyxrt.info, cls, None)
    if c:
        print(f"pyxrt.info.{cls}:", [a for a in dir(c) if not a.startswith('_')])
print("pyxrt.bo public:", [a for a in dir(pyxrt.bo) if not a.startswith('_')])
print("pyxrt.ext public:", [a for a in dir(pyxrt.ext) if not a.startswith('_')])
print("pyxrt.run public:", [a for a in dir(pyxrt.run) if not a.startswith('_')])
print("ert states:", [a for a in dir(pyxrt.ert_cmd_state) if not a.startswith('_')])
