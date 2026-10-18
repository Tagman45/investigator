module {
  aie.device(npu1) {
    %tile = aie.tile(0, 2)
    aie.runtime_sequence() {
      aie.end
    }
  }
}
