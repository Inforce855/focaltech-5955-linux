# FocalTech MOH matching-engine analysis — 5 November 2026

**Status:** Read-only REA/Ghidra research. **No change to the working Linux driver, libfprint, fprintd, PAM, KDE or isolated proprietary matcher.** Do not repeat previously successful enrolment/timing tests.

## Evidence and provenance

- Target: vendor `ftWbioEngineAdapter.dll`; SHA-256 `a4f037c260e8c86718675ddb6540467a9006ab26184858eb5b8726137185d57c`.
- REA 6.8.0 and Ghidra 12.1.4 via LM Studio Bionic, 5 November 2026.
- Function names stripped; procedure associations below were **inferred from diagnostic strings, string references and decompiled code**, not verified public exports or PDB symbols.
- Deep agent run spanned ~44 min 17 s with context compactions and observable Q8_0/Q4_K_M mixed-model activity. The recorded final `close_binary` call had empty arguments, returned success; no snapshot was requested.
- Claims below are **static decompilation observations** or explicitly identified inferences, not hardware-tested native parity.

## Matching procedures and direct call graph

| Inferred role | Ghidra address | Observed direct caller | Notes |
| --- | --- | --- | --- |
| `FtVerifyTwoTemplate` score-core candidate | `FUN_18003cab0` | `FUN_18000f740` (among others) | ~15 KB, numerous unresolved indirect calls; earlier agent interpretation as a name dispatcher was superseded but **implementation identity not definitive** |
| Verify adapter / result logger | `FUN_18000f740` | No resolved callers | Full pseudocode studied; zero resolved callers does **not** prove export status |
| `FtComputeDescriptors` candidate | `FUN_1800c7510` | `FUN_1800beb70` | 6 inferred parameters; ~11,487 UTF-16 pseudocode code units |
| `FtRansacNew` candidate | `FUN_180076f20` | `FUN_1800409f0` | 5 inferred parameters; ~22,245 UTF-16 pseudocode code units |

The three named matching-related candidates **do not directly call one another in the resolved callee lists**. This does **not** prove independent execution: indirect calls and their orchestrating paths are incompletely resolved. In particular, do not invent a descriptors→RANSAC→verification direct chain.

## Decompilation findings

**Verify adapter — `FUN_18000f740` (reported):**
- Receives two raw template descriptions (type and length), a caller-provided integer score threshold, six-float transform matrix and `overlapArea` output.
- Converts both raw templates through `FtDataToFocalTemplate` candidate `FUN_18002bc70`, then calls the score-core candidate `FUN_18003cab0(A,B,matrix,1)`. Also evaluates the reverse comparison and retains the larger score.
- Reports success at **`score >= threshold`** (return `0`); failure `-2`; `-1` null input, `-3` sample conversion error, `-4` stored conversion error. Percentage overlap calculated from in-bounds matched points / grid × 100. **Threshold is an input, not proven constant.**

**Descriptor candidate — `FUN_1800c7510` (reported):**
- SIFT-style Gaussian-pyramid gradients and orientation histograms, orientation normalisation to `[0,2π)`, eight angular bins (`angle * 4/π`, masked `&7`), bilinear spatial interpolation.
- Spatial cell values 3.0 or 4.5 according to `DAT_180225c8d`; histogram normalisation/quantisation dispatch at `DAT_180225c8f` to `FUN_1800c8e60`, `FUN_1800c98e0` or `FUN_1800ca1d0`. **These target bodies were not examined.**
- Treat the exact feature structure and field interpretations as provisional until checked.

**RANSAC candidate — `FUN_180076f20` (reported):**
- Checks `setLength > 2` (at least three); pairwise Euclidean distances `sqrt(dx²+dy²)`; consensus/inlier comparison **`abs(d1-d2) < 2.0`**.
- Uses `pDArray`, `pImportance`, `pConsTmp1`, `pConsTmp2` and tracks maximum consensus.
- Observed candidate returns `0xFFFFFFFF` (null sets) and `0xFFFFFFFE` (allocation failure). These apply to the RANSAC candidate; **do not conflate with verify-adapter error codes**.

## Confirmed limits and existing project objective

**Not established:** full parameter/feature layouts, raw FocalTech template format and conversion algorithm, exact descriptor normalisation/quantisation, all indirect call targets, complete matching score computation, bit-exact native algorithm, cross-session accuracy or secure template storage.

**One concrete remaining native-matching requirement:** establish the exact descriptor normalisation/quantisation chosen by `DAT_180225c8f` from the three target procedures before claiming compatible descriptor output. Existing proprietary MOH bridge remains the functioning experimental baseline; native work is still research, not ready to replace it.

**Project priorities remain unchanged:** protect the known-good verify-only libfprint/relay and password fallback; separately resolve either-index identification, service packaging/rollback and security boundaries. No speculative fingerprint/PAM rebuild or new timing experiment is justified by this static analysis.

**Agent workflow analysis:** [Local-AI-Linux-Lab Bionic/REA report](https://github.com/Inforce855/Local-AI-Linux-Lab/blob/main/benchmarks/bionic-rea-moh-investigation-2026-11-05.md).
