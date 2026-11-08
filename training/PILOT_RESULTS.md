# Flowers-102 small-batch fine-tuning pilot

Completed on 2026-11-08. This is a real CPU training run, not a proposed configuration. The live Leafnote app has NOT been changed.

## Scope

Oxford Flowers-102 covers 102 flower categories, including sunflower and English marigold. It is a deliberately smaller experiment than the planned PlantCLEF expansion and cannot replace a broad plant model by itself. Category names are common-name classes, not a standardized species taxonomy.

Official dataset: https://www.robots.ox.ac.uk/~vgg/data/flowers/102/
Authors: Maria-Elena Nilsback and Andrew Zisserman, Automated flower classification over a large number of classes, ICVGIP 2008.

## Training actually performed

- ImageNet-pretrained MobileNetV3 Small, with a new 102-output classification head.
- 30 head-training epochs on cached frozen features, batch size 16.
- 5 fine-tuning epochs of the final three feature blocks plus classifier, batch size 8. Earlier feature blocks and batch-normalization statistics remain frozen.
- Image augmentation during fine-tuning. AdamW. Seed 42. Four CPU threads, no GPU or paid service.
- The selected fine-tuned checkpoint achieved 90.09% validation accuracy, compared with 89.79% for the best frozen-feature head. Selection used validation only.
- Actual feature parameters changed. Training logs and weights are saved. The selected model uses the same architecture and standard ImageNet normalization, resize 256 then centre crop 224.

## Evaluation

| Measurement | Result |
| --- | --- |
| Training images | 1019 |
| Validation images | 1019 |
| Held-out test images | 6147 |
| Top-1 test accuracy | 87.10% |
| Top-3 test accuracy | 94.73% |
| Macro-average class recall | 88.99% |
| Sunflower correct | 39 / 41 (95.12%) |
| English marigold correct | 35 / 45 (77.78%) |

These figures measure this dataset only. They do not establish accuracy on arbitrary user photos or plants outside the 102 categories. This was one seed and one hyperparameter configuration, not an extensive model comparison. No photograph supplied by the user was available for testing their original sunflower example.

## Split hygiene

Used organizer train/validation/test IDs. SHA-256 duplicate screening removed four exact duplicates, prioritizing retention in test, then validation, then training (2 test duplicates, 1 validation duplicate and 1 training duplicate removed). Image IDs, removal counts and all class results are retained. Perceptual near-duplicates and photographer-level overlap were not audited. Test images were evaluated only after validation-based checkpoint selection.

## Reproduce

Install pilot-requirements.txt with the PyTorch CPU wheel index for torch/torchvision. Obtain the official 102flowers.tgz, imagelabels.mat, setid.mat and categories.html; extract jpg/ beside those metadata files.

```sh
python training/cpu_pilot.py --data /path/to/flowers --output /path/to/run --epochs 5
```

The code maps common names to class IDs using the organizers' category thumbnails and imagelabels.mat, rather than assuming alphabetical order. Use only trusted PyTorch checkpoints. The saved best.pt contains a state dictionary for mobilenet_v3_small with its final classifier replaced by Linear(1024,102).

No dataset photographs are redistributed. Dataset-image rights were not treated as a blanket licence for public redistribution. The artifact contains weights, run metadata and source only. Review applicable terms before any commercial distribution.

## Deployment status

Research checkpoint only. Before shipping: validate export parity, add compatible label metadata, test speed and memory in the browser, and establish how to handle flowers outside the 102 categories. Do not silently replace the existing 1,081-class plant identifier with this narrower flower model.
