# M4 Fix typed-lsof parser verification

PASS: the complete hermetic suite ran 96 methods with zero failures or errors and exit status 0. Ten focused typed-lsof methods were added. All 86 prior methods remain: 83 are AST-identical to HEAD; three contain only the exact -Fpcfnt and t-field fixture updates, with their prior assertions unchanged.

The generated positive fixture contains 24,000 file records across 600 process groups. It includes the observed empty-name non-path types and exact fp./twd descriptors. It is synthetic and does not reproduce private live lsof output. Negative tests cover blank filesystem and unknown types, field order and completeness, ambiguous paths, and target handles following the large inventory.

- Full log: `lsof-typed-parser-suite.log`
- Structured receipt: `M27-lsof-typed-parser.json`
- Runtime SHA-256: `fc21d00abf306467c9022dc066ff033731ba84be19aaf9a21ffe032c0ca265f2`
- Policy SHA-256: `c567b56e56aad04bcfcbf10ff416906be12427709b80a9740fe5553dc55b96b9`
- Core SHA-256: `5b1f13f415996faf7f6c6416359267866a4f91e1cdaa5ba5b42abc9b06f2d58e`
- Test SHA-256: `e98e95cd9788519b639d4690c05bd98bba7c1918e28e28e9d1f923b25c63a65e`
- Log SHA-256: `33166483b2d4eb1c6cfaeb9fadc15b08e21986582b7ba3f0d14887a98a9266a1`
- Retained synthetic directory: `/private/tmp/m4-guard-hermetic-01nseg65`

No production operations were performed by this test subtask. Parent M4 Fix owns independent review, publication, deployment, remote CI verification and any real grant retry.
