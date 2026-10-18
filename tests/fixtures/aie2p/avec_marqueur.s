## @ bundle 1
vmov cml1, r0
vmac.f dm1, dm1, x3, x7
vmac.f dm2, dm2, x5, x9
vadd.f dm3, dm1, dm2
vsub.f dm4, dm3, dm1
vconv.bf16.fp32 x3, cml4
vups.4x dm3
## @ bundle 2
nop
nop
