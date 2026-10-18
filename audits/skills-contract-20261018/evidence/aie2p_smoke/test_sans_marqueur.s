// synthetic AIE2p kernel for smoke test
vmov cml1, r0
vmac.f dm1, dm1, x3, x7 ; vmac.f dm2, dm2, x5, x9 ; vadd.f dm3, dm1, dm2 ; vsub.f dm4, dm3, dm1 ; vconv.bf16.fp32 x3, cml4 ; vst.conv.bf16.fp32 cml0, r2 ; vups.4x dm3
nop ; nop ; nop ; nop ; nop ; nop ; nop
