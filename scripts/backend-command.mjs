import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import process from "node:process";

const root = resolve(import.meta.dirname, "..");
const backend = resolve(root, "backend");
const environmentPath = resolve(root, ".env");
if (existsSync(environmentPath)) process.loadEnvFile(environmentPath);
if (!process.env.CYBERMENTOR_DATABASE_URL) {
  const databasePath = resolve(backend, "cybermentor-dev.sqlite3").replaceAll(
    "\\",
    "/",
  );
  process.env.CYBERMENTOR_DATABASE_URL = `sqlite+pysqlite:///${databasePath}`;
}
process.env.CYBERMENTOR_ENVIRONMENT ||= "development";
process.env.CYBERMENTOR_EMAIL_BACKEND ||= "console";
process.env.CYBERMENTOR_CONTENT_ROOT ||= resolve(root, "content", "published");
const python = resolve(
  backend,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const command = process.argv[2];
const forwarded = process.argv.slice(3);
const localSeedCommands = new Set(["seed-dev-local"]);

if (!existsSync(python)) {
  process.stderr.write(
    "Backend virtual environment is missing. Run npm run setup:local first.\n",
  );
  process.exitCode = 1;
} else {
  const definitions = {
    migrate: ["-m", "alembic", "upgrade", "head"],
    "migration-status": ["-m", "alembic", "current"],
    verify: ["-m", "app.db.verify"],
    rollback: ["-m", "alembic", "downgrade", "-1"],
    seed: ["-m", "app.db.seed"],
    "seed-dev": ["-m", "app.db.dev_seed"],
    "seed-dev-local": ["-m", "app.db.dev_seed"],
    test: ["-m", "pytest"],
    lint: ["-m", "ruff", "check", "app", "tests"],
    typecheck: ["-m", "mypy", "app"],
    format: ["-m", "ruff", "format", "--check", "app", "tests"],
  };
  const args = definitions[command];
  if (!args) {
    process.stderr.write(
      `Unknown backend command: ${command || "(missing)"}.\n`,
    );
    process.exitCode = 1;
  } else {
    const commandEnvironment = { ...process.env };
    if (localSeedCommands.has(command)) {
      commandEnvironment.CYBERMENTOR_ENVIRONMENT = "development";
      commandEnvironment.CYBERMENTOR_DEV_SEED_ENABLED = "true";
    }
    const result = spawnSync(python, [...args, ...forwarded], {
      cwd: backend,
      env: commandEnvironment,
      stdio: "inherit",
      windowsHide: true,
    });
    if (result.error) {
      process.stderr.write(`${result.error.message}\n`);
      process.exitCode = 1;
    } else {
      process.exitCode = result.status ?? 1;
    }
  }
}
