# Expanded plant model: training preparation

Status: preparation only. No new model has been trained or deployed.

## Dataset selected for audit

PlantCLEF 2024 single-plant training data, reused by PlantCLEF 2026. Organizers report approximately 1.4 million images and 7,806 species, focusing on southwestern Europe. The smaller archive is approximately 160 GB. This is not worldwide exhaustive coverage.

Official sources:
- https://www.imageclef.org/PlantCLEF2026
- https://lab.plantnet.org/LifeCLEF/PlantCLEF2024/single_plant_training_data/PlantCLEF2024singleplanttrainingdata.csv
- https://lab.plantnet.org/LifeCLEF/PlantCLEF2024/single_plant_training_data/PlantCLEF2024singleplanttrainingdata_800_max_side_size.tar
- https://docs.plantnet.org/en/reference/data-and-image-licensing/

The metadata header and initial records were inspected. They contain species names, original split, observation ID, author, per-image licence and backup URL. Full metadata retrieval and sunflower coverage verification are still pending. The preparation script refuses a dataset without Helianthus annuus training examples.

Only explicit CC0, CC BY and CC BY-SA metadata rows are retained. Unknown and noncommercial licences are excluded, so the final count will differ from the organizer's totals. Keep the manifest with contributor/source/licence information; verify source terms before redistributing data or weights. Do not commit photos, location metadata or checkpoints to this repository. The manifest intentionally omits coordinates.

## Compute and storage

This chat workspace has no CUDA GPU. A full run has NOT started. Use a GPU machine with at least 200 GB for extracted images, and substantially more if retaining the tar archive as well. Free notebook sessions may not offer enough storage or uninterrupted time. No paid resources have been provisioned.

## Run

Install a compatible PyTorch + torchvision CUDA pair from https://pytorch.org/get-started/locally/ and Pillow and NumPy. Download the complete official metadata and image archive on the training machine. Extract images, then pass the root containing train/, val/ and test/ to --images.

```sh
python training/prepare.py /data/metadata.csv /data/prepared
python training/train.py --manifest /data/prepared/manifest.jsonl --images /data/images --output /data/runs/mobilenet-large
```

Use --resume with a trusted last.pt checkpoint and the same output directory to continue an interrupted run. Preserve best.pt alongside last.pt. Downloaded metadata must be complete, not the partial local inspection file.

## Method

Fine-tune all layers of ImageNet-pretrained MobileNetV3 Large, with a new classifier matching the audited plant taxonomy. This is a new fine-tuning run, not a relabelling of the existing 1,081-output ONNX file. Use augmented training images, a smaller backbone learning rate, AdamW and cosine scheduling. Preserve organizer splits and fail on cross-split observation IDs or duplicate filenames. Retain a validation-selected checkpoint and evaluate it once on the single-plant test split. Report top-1, top-3, macro recall, per-class support/recall and sunflower recall. No accuracy target has been achieved yet.

## Before publishing a replacement

1. Finish the metadata/licence/coverage audit and inspect train/validation/test class distributions.
2. Check exact/perceptual duplicate images across splits and audit observation grouping.
3. Run and log training, then evaluate the chosen checkpoint. Do not tune on test results.
4. Compare with the current model on their shared species; report added species separately.
5. Add independent sunflower, Calendula, other similar flowers and unsupported/non-plant photos to an external check set.
6. Export ONNX and compare its logits against PyTorch on real held-out images.
7. Update the app's fixed 1,081-label validation, taxonomy and preprocessing. The candidate expects resize 232 then crop 224; the existing app's 256-based crop is incompatible.
8. Test browser speed, memory and unknown-plant behaviour. Do not equate softmax scores with calibrated correctness.

The scripts have syntax and synthetic metadata checks, but full PyTorch execution is unverified because this workspace lacks the training dependencies/GPU. Current live app remains unchanged.
