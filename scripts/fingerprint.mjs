import { readFile, writeFile, rename } from "node:fs/promises";
import { createHash } from "node:crypto";
import { basename, extname } from "node:path";

// One source-derived revision keeps the HTML, modules, worker and profiles together.
export async function fingerprint(directory) {
  const paths = [
    "style.css",
    "src/app.js",
    "src/classifier.js",
    "src/model-worker.js",
    "src/profiles.js",
    "assets/species.json",
    "assets/profiles.json",
  ];
  const contents = await Promise.all(
    paths.map((path) => readFile(`${directory}/${path}`, "utf8")),
  );
  const revision = createHash("sha256")
    .update(contents.join("\0"))
    .digest("hex")
    .slice(0, 12);
  const replacements = paths.map((path) => {
    const old = basename(path);
    return [
      old,
      old.slice(0, -extname(old).length) + "." + revision + extname(old),
    ];
  });
  for (const path of ["index.html", ...paths]) {
    let content = await readFile(`${directory}/${path}`, "utf8");
    for (const [from, to] of replacements)
      content = content.replaceAll(from, to);
    await writeFile(`${directory}/${path}`, content);
  }
  for (const [index, path] of paths.entries()) {
    await rename(
      `${directory}/${path}`,
      `${directory}/${path.replace(basename(path), replacements[index][1])}`,
    );
  }
  await writeFile(`${directory}/version.json`, JSON.stringify({ revision }));
  return revision;
}
