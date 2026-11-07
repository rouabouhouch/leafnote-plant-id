# Leafnote

A focused plant photo identifier that runs a pretrained vision model locally in the browser, returns three suggestions and offers source-linked botanical descriptions.

[Open the app](https://rouabouhouch.github.io/leafnote-plant-id/)

## What it does

- Accepts JPG, PNG and WebP photos, with drag and drop and four real example photos.
- Runs MobileNetV3 Small through ONNX Runtime Web in a Web Worker.
- Shows three candidates from 1,081 supported species and explains that model scores are not calibrated correctness probabilities.
- Looks up Wikipedia profiles by scientific name, with sources and a Kew botanical-record search link. Four example profiles are cached.
- Keeps photo pixels on the device. No backend, API keys, paid inference, login, analytics or photo storage. Hosting and Wikipedia still receive ordinary web requests. Google Fonts supplies the fonts.

This version uses a pretrained model, not a newly trained model. It does not use an LLM. Wikipedia profiles provide useful sourced background without inference fees or generated care instructions. An LLM should only be added with grounded source material, clearly labelled generated text and an explicit cost/privacy choice.

## Limits

This is an exploratory field guide, not a definitive identifier. Plants outside the class list can receive confident-looking incorrect results. The app does not reliably detect unknown species. The crop assumes one plant near the centre. The softmax and score-gap warning are display heuristics, not calibrated uncertainty or out-of-distribution detectors. Never rely on its results for eating, medicinal use or pet safety.

## Model and reproducibility

- Model author [cpoisson](https://huggingface.co/cpoisson/plantnet300k-mobilenetv3-small), PlantNet-300K MobileNetV3 Small.
- Pinned revision `b7505ed8cf49fea221c2bb0eae83239f066f32bb`, file `plantnet_mobilenetv3.onnx`.
- The available ONNX is the v1 export. The author's model card reports v1 top-1 accuracy of 73.89% and top-5 of 91.86% on their test split. Those are author-reported dataset metrics, not measured accuracy of this app, and not the higher v2 PyTorch results.
- Preprocessing approximates resize-short-side 256 followed by centre crop 224 in a high-quality browser canvas resample, converts RGB to float32 NCHW, and applies ImageNet means and standard deviations. Interpolation can differ from the original torchvision pipeline and the Node spot-check pipeline.
- Labels follow the sorted seven-digit species IDs used by ImageFolder. The species count is validated at runtime.
- ONNX Runtime Web is pinned to 1.20.1. Both runtime and model downloads are SHA-256 verified during build. All inference assets are then served from the app's own origin.

## Real-photo spot check

Four CC0 iNaturalist research-grade observation photos were checked with the shipped ONNX model, class mapping and normalization using ONNX Runtime WASM in Node. These photos were not selected after viewing predictions. This small convenience sample is not an independent benchmark and training overlap has not been audited.

| Expected species | Top suggestion | Top score | Expected rank |
| --- | --- | --- | --- |
| Cirsium vulgare | Daucus carota | 76.2% | 2 |
| Lavandula dentata | Lavandula dentata | 87.9% | 1 |
| Nymphaea alba | Nymphaea alba | 88.2% | 1 |
| Papaver rhoeas | Papaver rhoeas | 98.6% | 1 |

The thistle failure is deliberately retained in the app. A high score alone is not a reliability guarantee. Browser results can differ because of image resampling. Photo observers, original observations and source URLs are recorded in [samples/index.json](samples/index.json).

## Run and deploy

Requires Node.js 22, curl and Python 3 for the optional local server. No npm package installation is needed.

```sh
npm test
npm run build
npm start
```

The build downloads about 22 MB of pinned model/runtime assets and fails if their hashes differ. Output is `dist/`. In GitHub Settings → Pages, choose GitHub Actions. Every push to main runs tests, builds and deploys through `.github/workflows/pages.yml`.

## Structure

- `src/classifier.js` is pure crop, normalization, label and ranking logic.
- `src/model-worker.js` owns model initialization and inference away from the UI thread.
- `src/profiles.js` owns profile retrieval and cached examples.
- `src/app.js` coordinates files, request IDs, candidate selection and accessible DOM rendering.
- `scripts/build.mjs` packages static assets and checks third-party integrity.
- `tests/` checks inference preprocessing, numerical stability and taxonomy assumptions.

No secrets belong in this repository. A new upload supersedes older results, and profile lookups are cancelled when another plant is selected.

## Attribution and licences

Application code is MIT licensed. Third-party assets retain their own terms.

- Model and species mapping by cpoisson, model card declares OpenRAIL. See the [pinned repository](https://huggingface.co/cpoisson/plantnet300k-mobilenetv3-small/tree/b7505ed8cf49fea221c2bb0eae83239f066f32bb) for model terms and dataset attribution.
- ONNX Runtime Web by Microsoft, [MIT licence](https://github.com/microsoft/onnxruntime/blob/v1.20.1/LICENSE).
- Example photos are CC0, credited in `samples/index.json`. They are resized JPEG copies of the linked originals.
- Cached and live descriptions are from Wikipedia contributors, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Original article URLs accompany each description in `assets/profiles.json` and the app. Cached summaries were retrieved on 2026-11-07.
- DM Sans and DM Serif Display are supplied through Google Fonts under the SIL Open Font License.
