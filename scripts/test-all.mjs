import { spawnSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { basename, join, relative, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const vitest = resolve(root, "node_modules/vitest/vitest.mjs");

function discover(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return discover(path);
    return /\.test\.(mjs|ts|tsx)$/.test(entry.name) ? [path] : [];
  });
}

const files = ["src", "server", "scripts"]
  .flatMap((directory) => discover(resolve(root, directory)))
  .sort();
const pipeline = files.filter(
  (file) => basename(file) === "content-pipeline.test.mjs",
);
const browser = files.filter((file) => file.endsWith(".test.tsx"));
const general = files.filter(
  (file) => !pipeline.includes(file) && !browser.includes(file),
);
const groups = [general, pipeline, browser].filter((group) => group.length);

for (const group of groups) {
  const labels = group.map((file) => relative(root, file));
  process.stdout.write(
    `\nRunning ${labels.length} test file(s): ${labels.join(", ")}\n`,
  );
  const result = spawnSync(
    process.execPath,
    [
      vitest,
      "run",
      ...group,
      "--reporter=default",
      "--pool=vmThreads",
      "--maxWorkers=1",
    ],
    { cwd: root, stdio: "inherit" },
  );
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}

process.stdout.write(`\nAll ${files.length} discovered test files passed.\n`);
