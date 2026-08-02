import { existsSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { resolve } from "node:path";
import process from "node:process";

const root = resolve(import.meta.dirname, "..");
const backend = resolve(root, "backend");
const isWindows = process.platform === "win32";
const venvPython = resolve(
  backend,
  ".venv",
  isWindows ? "Scripts/python.exe" : "bin/python",
);
const systemCandidates = isWindows
  ? [
      ["py", "-3.12"],
      ["python", []],
    ]
  : [
      ["python3", []],
      ["python", []],
    ];

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: backend,
    encoding: "utf8",
    stdio: options.quiet ? "pipe" : "inherit",
    env: { ...process.env, ...developmentEnvironment() },
  });
  if (result.status !== 0) {
    if (options.quiet) {
      process.stderr.write(result.stderr || "");
    }
    throw new Error(`${command} ${args.join(" ")} failed.`);
  }
  return result;
}

function developmentEnvironment() {
  const databasePath = resolve(backend, "cybermentor-dev.sqlite3").replaceAll(
    "\\",
    "/",
  );
  return {
    CYBERMENTOR_ENVIRONMENT:
      process.env.CYBERMENTOR_ENVIRONMENT || "development",
    CYBERMENTOR_DATABASE_URL:
      process.env.CYBERMENTOR_DATABASE_URL ||
      `sqlite+pysqlite:///${databasePath}`,
    CYBERMENTOR_EMAIL_BACKEND:
      process.env.CYBERMENTOR_EMAIL_BACKEND || "console",
    CYBERMENTOR_CONTENT_ROOT:
      process.env.CYBERMENTOR_CONTENT_ROOT ||
      resolve(root, "content", "published"),
  };
}

function findSystemPython() {
  for (const [command, candidateArgs] of systemCandidates) {
    const args = Array.isArray(candidateArgs) ? candidateArgs : [candidateArgs];
    const result = spawnSync(command, [...args, "--version"], {
      encoding: "utf8",
      stdio: "pipe",
    });
    if (result.status === 0) return { command, args };
  }
  throw new Error(
    "Python 3.12 or newer is required for the trusted API. Install Python and rerun npm run dev.",
  );
}

function ensureBackend() {
  if (!existsSync(venvPython)) {
    const python = findSystemPython();
    run(python.command, [
      ...python.args,
      "-m",
      "venv",
      resolve(backend, ".venv"),
    ]);
  }
  const importCheck = spawnSync(
    venvPython,
    ["-c", "import fastapi, sqlalchemy, alembic"],
    { cwd: backend, stdio: "ignore" },
  );
  if (importCheck.status !== 0) {
    run(venvPython, ["-m", "pip", "install", "-e", ".[dev]"]);
  }
}

function prepare() {
  ensureBackend();
  run(venvPython, ["-m", "alembic", "upgrade", "head"]);
  run(venvPython, ["-m", "app.db.seed"]);
  process.stdout.write(
    "Trusted API ready. Local npm development uses a durable SQLite adapter; Docker Compose uses PostgreSQL.\n",
  );
}

if (process.argv.includes("--prepare")) {
  prepare();
} else {
  ensureBackend();
  const child = spawn(
    venvPython,
    [
      "-m",
      "uvicorn",
      "app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      process.env.CYBERMENTOR_TRUSTED_API_PORT || "8010",
      "--reload",
    ],
    {
      cwd: backend,
      stdio: "inherit",
      env: { ...process.env, ...developmentEnvironment() },
    },
  );
  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => child.kill(signal));
  }
  child.on("exit", (code) => process.exit(code ?? 0));
}
