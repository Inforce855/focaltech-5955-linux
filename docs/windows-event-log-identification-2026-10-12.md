# Live FocalTech recognition in the Windows Application log — 12 October 2026

## Source and privacy

The device owner privately supplied an exported Windows **Application.evtx** log from their offline VirtualBox Windows guest. The log has **39 event records**. Only short, directly relevant FocalTech text and relative timing are reproduced here. **The original EVTX was not committed**: it also contains unrelated Windows configuration, licensing, application-crash and diagnostic metadata. No fingerprints, templates, source memory pointers or Windows user identity information are included.

The binary record headers show events written on **12 October 2026**, UTC, with precise FILETIME-derived timestamps.

## Actual failed-first, successful-second sequence

| UTC time | Selected sanitized FocalTech log entry |
| --- | --- |
| 14:48:56.922 | `Unsupported IOCTL - 0x440028.` — preceding the two capture outcomes; not evidence by itself of login failure |
| 14:48:58.072 | `IOCTL_BIOMETRIC_CAPTURE_DATA` requested |
| 14:48:58.082 | preceding capture request completed |
| 14:48:58.084 | new biometric capture request |
| 14:49:02.265 | `Got finger touched 1.` |
| 14:49:02.279 | capture request completed |
| 14:49:02.295 | `Identify ret = -4` |
| 14:49:02.295 | `NO MATCH: 6_14_0_47_39_47` |
| 14:49:02.302 | next capture request |
| 14:49:04.178 | `Got finger touched 1.` |
| 14:49:04.193 | second capture completed |
| 14:49:04.206 | `Identify Match: 3_f5_9_15_0` |
| 14:49:04.234 | third capture request |
| 14:49:05.405 | pending request canceled (consistent with authentication session ending, not proved) |

**Observed:** the first contact produced `NO MATCH`, and about **1.91 seconds later** a second contact produced `Identify Match`. The respective touch-to-result log gaps were about **30 ms** and **28 ms**. These are coarse event-message timing bounds; not precise measurement of detector execution, and do not imply that feature extraction alone took 28 ms. No fake-finger rejection string occurred in the relevant EVTX entries.

## Direct link to the vendor DLL's log formatting

Read-only disassembly of the matching private `ftWbioEngineAdapter.dll`:

- Exact format string `[%s] I: NO MATCH: %d_%d_%d_%d_%d_%d`, VA **`0x1801B23F0`**, referenced at **`0x18012AC7D`**.
- Exact format string `[%s] I: Identify Match: %d_%x_%d_%d_%d`, VA **`0x1801B2268`**, referenced at **`0x18012AE35`**.
- Failure log at `0x18012AC6D..ACB3` supplies its first value **`[context+0x24]-[context+0x20]`** and second value **`[context+0x24]`**. The failure record's `6_14` therefore implies that `[context+0x20] = 8`.
- Success path at `0x18012AE10` explicitly increments **`[context+0x20]`**, and the success log at `0x18012AE35..AE5F` supplies the third and fourth values from **`[context+0x20]`** and **`[context+0x24]`**, respectively. This yields the next result's `9_15`. The same path emits first and second numbers from separate recognition-result storage; their meaning is **not yet decoded**, and `f5` is hexadecimal (`%x`).

**Best-supported interpretation:** `[context+0x20]` counts successful recognitions; `[context+0x24]` counts identification attempts; their difference counts failed attempts. The emitted totals update coherently between the two live captures. The fields appear to persist across earlier history, since the log already shows fourteen total attempts at the first observed failure. The numeric values are **not evidence for six feature matches, fourteen keypoints or a six-tumbler matching threshold**.

Other failure-log fields (`0`, `47`, `39`, `47`) originate from `[context+0x2c]` and three globals at `0x1803A9798`, `0x1803A979C`, `0x1803A97A4`. Their semantics are unresolved. The success message's `3`, hexadecimal `f5` and trailing `0` also lack a verified semantic mapping beyond their operand sources.

## Very important: what `algoInfo` stores

The user had identified the driver's INF default `algoInfo = ALGO_0_0_0_0_0_E`. The engine DLL embeds **`ALGO_%d_%d_%d_%d_%d_E`**, VA **`0x1801B1A90`**.

The code at **`0x1801291DF..1291F3`** reads these **five decimal values** from the existing configuration text into counters/fields at context offsets `+0x20`, `+0x24`, `+0x28`, `+0x2c`, `+0x34`, via a scan/parse helper.

The code at **`0x1801292FC..129334`** writes the same five fields back into an `ALGO_%d_%d_%d_%d_%d_E` string using an output formatting helper, then saves it via a storage/configuration helper. The first two parsed fields are exactly the counters updated in the live success/failure logs.

**Conclusion:** `ALGO_0_0_0_0_0_E` is **not a reliable way to infer which MFB/MFS feature extraction mode is selected**. It stores at least accumulated recognition statistics, despite the name `algoInfo`. The actual feature-extractor dispatch still uses a separate byte at `0x180225C51` (compiled initial value 1), whose runtime value remains unverified.

No `ALGO_...` values, firmware model, fake-finger rejection reason, or runtime extractor mode were exposed in the shared EVTX record messages.

## Next bounded research step

- Confirm the meaning of the remaining two success-result fields and failure-score globals using **offline instruction tracing and synthetic records only**.
- Locate a non-invasive source of **quality/rejection category** codes to explain the first attempt, without assuming it was spoof rejection.
- Keep the real Windows Hello login and biometric sensor unchanged; do not replay fingerprint packets into authentication.
