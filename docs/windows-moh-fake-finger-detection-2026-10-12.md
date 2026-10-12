# FocalTech 5955 matching engine — independent fake-finger / presentation-attack checks

**12 October 2026.** Read-only inspection of the owner's actual matching MOH `ftWbioEngineAdapter.dll`, not other FocalTech packages. No real fingerprint images, templates, Windows Hello recordings, model weights, spoofing examples, or proprietary binaries are included.

Private binary SHA256: `a4f037c260e8c86718675ddb6540467a9006ab26184858eb5b8726137185d57c`; x64 PE image base `0x180000000`.

## Direct binary evidence

The vendor engine includes:

- `focal_SetFakeFingerDetect` and `focal_SetFakeFingerNetParam` — dedicated configuration entry points.
- `focal_FakeFingerPredict` and `FtFakeFingerPredict_Method2` — named prediction methods, suggesting the engine can use more than one classification approach.
- `predict_FW9391_FakeFinger`, `predict_FW9395_FakeFinger`, `predict_FW9398_FakeFinger`, `predict_FW9397_FakeFinger`, `predict_FW9399_FakeFinger`, `predict_FW9362_FakeFinger`, `predict_FW9372_FakeFinger`, and `predict_FW9349_FakeFinger` — **several firmware/chip-family variants in a shared compiled DLL**. The presence of any string does **not** establish which variant runs on hardware `2808:5955`.
- Corresponding `FakeFingerFW…NetMaxPool` functions, plus `FakeFinger_NetStruct_Param_Set`. Predict + NetStruct + MaxPool strongly indicate an **embedded neural-network-based presentation-attack classifier**. Its architecture, trained weights, input geometry, model-selection conditions, and whether the shipped device invokes this path remain unconfirmed.
- Configuration/debug names `fakeFingerDetectMode`, `fakeFingerDetectMethod`, `fakeFingerDetectSensitivity`, `ForeignBodyAttackEn`, and diagnostic `noneFingerRate = %f, fakeFingerRate = %f`.
- The explicit diagnostic `focaltech-lib:%s...identify FAIL, is fake finger!, ret = %d, rate = %f`. Crucially, this is an **identification-result failure path**, not just a speculative source symbol.

### Cross-reference confirmation — not merely strings

In disassembly of the verified DLL, a prediction wrapper at `0x18000AB80` calls the prediction method at `0x180033CA0`, then evaluates the reported classification against configured policy and exposes a Boolean-like result. The identification routine contains **two direct calls** to this wrapper (at `0x1800275BE` and `0x1800277A4`); the adjacent control-flow branches include the above **identify FAIL, is fake finger** log. This confirms that fake-finger prediction **can gate identification**, separately from the 45-sample/256-bit feature descriptor and the three-correspondence geometric RANSAC prerequisite.

These calls are **conditional** on engine configuration. We have not observed the configuration during the real successful Windows Hello login, so cannot say which anti-spoofing checks were enabled, whether a specific model was invoked, or why a particular press was rejected.

The DLL also references `focal_SetForeignBodyAttackSwitch` and logs **`after foreignBody, m`** and **`after foreignBody and BinCheck, m`**, suggesting additional quality or foreign-material validation used in some matching pathways. These are distinct from the neural prediction names; exact behavior and invocation order are unverified.

## Relationship to the earlier 3-point and 45-position discoveries

**These represent different stages and units:**

1. **Capture and quality / presentation-attack checks:** the device produces a full image; the engine can assess contact/coverage and classify real/fake patterns, depending on its configuration.
2. **Feature extraction:** in the compiled initial MFB mode, each selected local feature is described using **45 rotated intensity-sampling positions**, compared in 256 binary pairs. This is not a command to the sensor to collect 45 separate images.
3. **Matching geometry:** the separately traced `FtRansacNew` routine expects at least **three candidate correspondences** before fitting a transformation. Three points are **not** a proven anti-spoofing threshold or the final Windows Hello acceptance threshold.
4. **Decision:** recognition scores, overlap, and any configured quality/presentation checks determine the final result; their exact ordering is not fully reconstructed.

A successful second press after a rejected first press could reflect contact coverage, image quality, failure to find enough matching features, geometric misalignment, or presentation-attack rejection. **The current observations do not identify the cause**, and a fast success does not demonstrate that a liveness classifier was skipped.

## Next analysis without disturbing the working reference

- Locate how the engine selects a chip-family prediction model **at runtime**, using read-only DLL control-flow inspection. Do not infer `FW9395` merely from the function's presence.
- Determine which **stage** of the identification flow runs the quality checks, fake-finger classification and feature matching, and how errors are distinguished. Record only stage ordering and sanitized return-code categories.
- If investigating actual first/second-attempt failures later, prefer **official non-biometric status/event messages** without collecting, altering, replacing, or publishing real fingerprint frames and templates.
- Do not disable anti-spoofing, weaken configuration, patch the DLL, or inject samples into the Windows Hello authentication path.

To inspect named strings in the existing private DLL offline on Nobara:
```bash
strings -a /path/to/private/ftWbioEngineAdapter.dll | grep -Ei 'fake.?finger|foreign.?body|BinCheck'
```

The independent 5955 image conversion and image descriptor research remain documented in [image converter](windows-image-converter-prototype-2026-10-12.md) and [feature extraction](windows-moh-feature-extraction-disassembly-2026-10-12.md).
