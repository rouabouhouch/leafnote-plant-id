# Live validation

Verified on 2026-11-07 in the cloud Chrome browser at https://rouabouhouch.github.io/leafnote-plant-id/.

App revision `1728041441fb`, deployment source commit `20f1123a6efeb70a6747ee8d4b2904f9125d5271`.

The GitHub Actions tests, integrity-checked build and Pages deployment completed successfully. The loaded HTML referenced `src/app.1728041441fb.js`, confirming that the final high-quality image resampling code was served rather than an older cached module.

| Example photo | Top suggestion | Relative model score | Expected species rank |
| --- | --- | --- | --- |
| Common poppy | Papaver rhoeas | 98.3% | 1 |
| French lavender | Lavandula dentata | 94.5% | 1 |
| European white waterlily | Nymphaea alba | 77.9% | 1 |
| Bull thistle | Daucus carota | 68.2% | 3 (Cirsium vulgare, 9.4%) |

These four photos are a small convenience sample, not an accuracy benchmark. Browser image interpolation differs from the Node/Sharp spot check documented in the README. All four samples use the same File decoding and model pipeline as a selected user photo. A separate operating-system file-picker upload and mobile-device runtime were not tested.

Also verified through the live UI:

- Selecting a different candidate retrieves its profile.
- A non-cached Papaver orientale profile loads from Wikipedia with a source link.
- Scientific-name search filters the supported class list.
- Subsequent photos reuse the initialized worker model.
- The failed thistle identification remains available as a visible example of the model's limitations.

The app supports a fixed label set, including some hybrids, broad genus labels and duplicate taxonomic names. It cannot reliably reject unsupported plants. Scores should never be treated as calibrated correctness probabilities.

