export const SIZE = 224;
const MEAN = [0.485, 0.456, 0.406];
const STD = [0.229, 0.224, 0.225];

export function centerCrop(width, height) {
  if (!(width > 0 && height > 0))
    throw new Error("The image has no readable dimensions.");
  const side = (Math.min(width, height) * SIZE) / 256;
  return [(width - side) / 2, (height - side) / 2, side, side];
}

export function normalize(rgba) {
  const pixels = SIZE * SIZE;
  if (rgba.length !== pixels * 4) throw new Error("Invalid input size.");
  const result = new Float32Array(pixels * 3);
  for (let channel = 0; channel < 3; channel++) {
    for (let i = 0; i < pixels; i++) {
      result[channel * pixels + i] =
        (rgba[4 * i + channel] / 255 - MEAN[channel]) / STD[channel];
    }
  }
  return result;
}

export function classNames(mapping) {
  const keys = Object.keys(mapping).sort();
  if (
    keys.length !== 1081 ||
    !keys.every(
      (key) => /^\d{7}$/.test(key) && typeof mapping[key] === "string",
    )
  ) {
    throw new Error("The species list does not match this model.");
  }
  return keys.map((key) => mapping[key]);
}

export function rank(logits, labels) {
  if (logits.length !== labels.length || !logits.every(Number.isFinite))
    throw new Error("Unexpected model output.");
  const max = Math.max(...logits);
  const exps = Array.from(logits, (value) => Math.exp(value - max));
  const sum = exps.reduce((a, b) => a + b, 0);
  return labels
    .map((name, index) => ({ name, score: exps[index] / sum }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
}

export function searchName(label) {
  const words = label.trim().split(/\s+/);
  if (words[1] === "x" || words[1] === "×")
    return [words[0], "×", words[2]].join(" ");
  return words.slice(0, 2).join(" ");
}
