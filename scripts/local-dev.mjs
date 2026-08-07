import { randomBytes } from "node:crypto";
import { spawn, spawnSync } from "node:child_process";
import {
  existsSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { createServer } from "node:net";
import { resolve } from "node:path";
import process from "node:process";

const root = resolve(import.meta.dirname, "..");
const backend = resolve(root, "backend");
const environmentPath = resolve(root, ".env");
const environmentExamplePath = resolve(root, ".env.example");
const isWindows = process.platform === "win32";
const venvPython = resolve(
  backend,
  ".venv",
  isWindows ? "Scripts/python.exe" : "bin/python",
);
const viteEntry = resolve(root, "node_modules", "vite", "bin", "vite.js");
const requiredNode = { major: 22, minor: 12 };
const inheritedPortOverrides = new Set(
  [
    "CYBERMENTOR_WEB_PORT",
    "CYBERMENTOR_TRUSTED_API_PORT",
    "CYBERMENTOR_LEGACY_API_PORT",
  ].filter((name) => process.env[name] !== undefined),
);
const defaultPorts = {
  frontend: 5173,
  "trusted API": 8010,
  "content API": 8787,
};
const pythonCandidates = isWindows
  ? [
      { command: "py", args: ["-3.13"] },
      { command: "py", args: ["-3.12"] },
      { command: "python", args: [] },
    ]
  : [
      { command: "python3.13", args: [] },
      { command: "python3.12", args: [] },
      { command: "python3", args: [] },
      { command: "python", args: [] },
    ];

function fail(message) {
  throw new Error(message);
}

function parseEnvironment(text) {
  const values = {};
  for (const sourceLine of text.split(/\r?\n/)) {
    const line = sourceLine.trim();
    if (!line || line.startsWith("#")) continue;
    const separator = line.indexOf("=");
    if (separator < 1) continue;
    const key = line.slice(0, separator).trim();
    let value = line.slice(separator + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    values[key] = value;
  }
  return values;
}

function loadLocalEnvironment() {
  if (!existsSync(environmentPath)) return;
  const values = parseEnvironment(readFileSync(environmentPath, "utf8"));
  for (const [key, value] of Object.entries(values)) {
    if (process.env[key] === undefined) process.env[key] = value;
  }
}

function createLocalEnvironment() {
  if (existsSync(environmentPath)) {
    process.stdout.write("Local environment: existing .env preserved.\n");
    return false;
  }
  if (!existsSync(environmentExamplePath)) {
    fail("Missing .env.example; cannot create a local environment safely.");
  }
  const template = readFileSync(environmentExamplePath, "utf8");
  const generated = template.replaceAll(
    "__GENERATE_SECURE_LOCAL_VALUE__",
    () => randomBytes(32).toString("hex"),
  );
  writeFileSync(environmentPath, generated, {
    encoding: "utf8",
    flag: "wx",
  });
  process.stdout.write("Local environment: created .env with generated local secrets.\n");
  return true;
}

function commandResult(command, args, options = {}) {
  return spawnSync(command, args, {
    cwd: options.cwd ?? root,
    encoding: "utf8",
    stdio: options.quiet ? "pipe" : "inherit",
    env: options.env ?? process.env,
  });
}

function run(command, args, options = {}) {
  const result = commandResult(command, args, options);
  if (result.error) {
    fail(`Could not start ${command}: ${result.error.message}`);
  }
  if (result.status !== 0) {
    if (options.quiet) {
      process.stderr.write(result.stdout || "");
      process.stderr.write(result.stderr || "");
    }
    fail(
      `${options.label ?? command} failed with exit code ${result.status ?? "unknown"}.`,
    );
  }
  return result;
}

function verifyNodeVersion() {
  const [major, minor] = process.versions.node.split(".").map(Number);
  if (
    major < requiredNode.major ||
    (major === requiredNode.major && minor < requiredNode.minor)
  ) {
    fail(
      `Node.js ${requiredNode.major}.${requiredNode.minor} or newer is required; found ${process.versions.node}.`,
    );
  }
  process.stdout.write(`Node.js: ${process.versions.node}\n`);
}

function inspectPython(candidate) {
  const result = commandResult(
    candidate.command,
    [
      ...candidate.args,
      "-c",
      "import json,sys; print(json.dumps(list(sys.version_info[:3])))",
    ],
    { quiet: true },
  );
  if (result.status !== 0) return null;
  try {
    const version = JSON.parse(result.stdout.trim());
    if (
      Array.isArray(version) &&
      version.length === 3 &&
      version[0] === 3 &&
      [12, 13].includes(version[1])
    ) {
      return { ...candidate, version: version.join(".") };
    }
  } catch {
    return null;
  }
  return null;
}

function findPython() {
  for (const candidate of pythonCandidates) {
    const compatible = inspectPython(candidate);
    if (compatible) {
      process.stdout.write(`Python: ${compatible.version}\n`);
      return compatible;
    }
  }
  fail("Python 3.12 or 3.13 is required. Install it and rerun npm run setup:local.");
}

function localConfiguration() {
  const host = process.env.CYBERMENTOR_LOCAL_HOST || "127.0.0.1";
  const webPort = parsePort("CYBERMENTOR_WEB_PORT", 5173);
  const trustedPort = parsePort("CYBERMENTOR_TRUSTED_API_PORT", 8010);
  const legacyPort = parsePort("CYBERMENTOR_LEGACY_API_PORT", 8787);
  const databasePath = resolve(backend, "cybermentor-dev.sqlite3").replaceAll(
    "\\",
    "/",
  );
  return {
    host,
    webPort,
    trustedPort,
    legacyPort,
    databaseUrl:
      process.env.CYBERMENTOR_DATABASE_URL ||
      `sqlite+pysqlite:///${databasePath}`,
    contentRoot:
      process.env.CYBERMENTOR_CONTENT_ROOT ||
      resolve(root, "content", "published"),
  };
}

function parsePort(name, fallback) {
  const value = Number(process.env[name] || fallback);
  if (!Number.isInteger(value) || value < 1024 || value > 65535) {
    fail(`${name} must be an integer from 1024 through 65535.`);
  }
  return value;
}

function trustedEnvironment(configuration) {
  return {
    ...process.env,
    CYBERMENTOR_ENVIRONMENT:
      process.env.CYBERMENTOR_ENVIRONMENT || "development",
    CYBERMENTOR_DATABASE_URL: configuration.databaseUrl,
    CYBERMENTOR_EMAIL_BACKEND:
      process.env.CYBERMENTOR_EMAIL_BACKEND || "console",
    CYBERMENTOR_CONTENT_ROOT: configuration.contentRoot,
    CYBERMENTOR_FRONTEND_ORIGIN: `http://${configuration.host}:${configuration.webPort}`,
  };
}

function ensureNodeDependencies() {
  if (existsSync(viteEntry)) return;
  process.stdout.write("Node dependencies: installing from package-lock.json.\n");
  const npmCommand = isWindows ? "npm.cmd" : "npm";
  run(npmCommand, ["install", "--ignore-scripts"], {
    label: "Node dependency installation",
  });
}

function ensurePythonEnvironment({ install = false } = {}) {
  const systemPython = findPython();
  if (!existsSync(venvPython)) {
    process.stdout.write("Python environment: creating backend/.venv.\n");
    run(
      systemPython.command,
      [...systemPython.args, "-m", "venv", resolve(backend, ".venv")],
      { label: "Python environment creation" },
    );
    install = true;
  }
  const dependencyCheck = commandResult(
    venvPython,
    ["-c", "import alembic, argon2, fastapi, sqlalchemy, uvicorn"],
    { cwd: backend, quiet: true },
  );
  if (install || dependencyCheck.status !== 0) {
    process.stdout.write("Python dependencies: installing backend project.\n");
    run(venvPython, ["-m", "pip", "install", "-e", ".[dev]"], {
      cwd: backend,
      label: "Python dependency installation",
    });
  }
}

function prepareLocal({ fullSetup = false } = {}) {
  verifyNodeVersion();
  createLocalEnvironment();
  loadLocalEnvironment();
  if (fullSetup) ensureNodeDependencies();
  ensurePythonEnvironment({ install: fullSetup });
  const configuration = localConfiguration();
  const environment = trustedEnvironment(configuration);
  run(process.execPath, [resolve(root, "scripts", "seed-v1-academy.mjs")], {
    label: "Version 1 content seed",
  });
  run(venvPython, ["-m", "alembic", "upgrade", "head"], {
    cwd: backend,
    env: environment,
    label: "Database migration",
  });
  run(venvPython, ["-m", "app.db.seed"], {
    cwd: backend,
    env: environment,
    label: "Competition seed",
  });
  if (
    ["1", "true", "yes", "on"].includes(
      String(process.env.CYBERMENTOR_DEV_SEED_ENABLED || "").toLowerCase(),
    )
  ) {
    run(venvPython, ["-m", "app.db.dev_seed"], {
      cwd: backend,
      env: environment,
      label: "Development account seed",
    });
  }
  const databaseDescription = process.env.CYBERMENTOR_DATABASE_URL
    ? "configured CYBERMENTOR_DATABASE_URL"
    : resolve(backend, "cybermentor-dev.sqlite3");
  process.stdout.write(
    [
      "Local preparation complete.",
      `Database: ${databaseDescription}`,
      "Persistence: durable SQLite development adapter (PostgreSQL remains the production profile).",
      "",
    ].join("\n"),
  );
}

function portAvailable(host, port) {
  return new Promise((resolvePromise) => {
    const server = createServer();
    server.unref();
    server.once("error", () => resolvePromise(false));
    server.listen({ host, port, exclusive: true }, () => {
      server.close(() => resolvePromise(true));
    });
  });
}

async function preflightPorts(configuration) {
  const services = [
    ["frontend", configuration.webPort],
    ["trusted API", configuration.trustedPort],
    ["content API", configuration.legacyPort],
  ];
  const unavailable = [];
  for (const [name, port] of services) {
    if (await portAvailable(configuration.host, port)) continue;
    const environmentName = {
      frontend: "CYBERMENTOR_WEB_PORT",
      "trusted API": "CYBERMENTOR_TRUSTED_API_PORT",
      "content API": "CYBERMENTOR_LEGACY_API_PORT",
    }[name];
    if (
      inheritedPortOverrides.has(environmentName) ||
      Number(process.env[environmentName]) !== defaultPorts[name]
    ) {
      unavailable.push(`${name} ${configuration.host}:${port}`);
      continue;
    }
    let fallback = null;
    for (let candidate = port + 1; candidate <= port + 20; candidate += 1) {
      if (await portAvailable(configuration.host, candidate)) {
        fallback = candidate;
        break;
      }
    }
    if (fallback === null) {
      unavailable.push(`${name} ${configuration.host}:${port}`);
      continue;
    }
    configuration[{
      frontend: "webPort",
      "trusted API": "trustedPort",
      "content API": "legacyPort",
    }[name]] = fallback;
    process.stdout.write(
      `Port ${port} is unavailable; using ${fallback} for ${name}. Set ${environmentName} to force a specific port.\n`,
    );
  }
  if (unavailable.length) {
    fail(
      `Required port already in use: ${unavailable.join(", ")}. Stop the owning process or set the corresponding CYBERMENTOR_*_PORT value in .env.`,
    );
  }
}

function prefixOutput(stream, label, destination) {
  let pending = "";
  stream.setEncoding("utf8");
  stream.on("data", (chunk) => {
    pending += chunk;
    const lines = pending.split(/\r?\n/);
    pending = lines.pop() || "";
    for (const line of lines) destination.write(`[${label}] ${line}\n`);
  });
  stream.on("end", () => {
    if (pending) destination.write(`[${label}] ${pending}\n`);
  });
}

function stopProcessTree(child) {
  if (!child.pid || child.exitCode !== null) return;
  if (isWindows) {
    spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
      stdio: "ignore",
    });
  } else {
    child.kill("SIGTERM");
  }
}

async function waitFor(name, url, children, timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs;
  let lastFailure = "no response";
  while (Date.now() < deadline) {
    const exited = children.find(({ child }) => child.exitCode !== null);
    if (exited) {
      fail(
        `${exited.name} exited before startup completed (code ${exited.child.exitCode}).`,
      );
    }
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1_500) });
      if (response.ok) return;
      lastFailure = `HTTP ${response.status}`;
    } catch (error) {
      lastFailure = error instanceof Error ? error.message : String(error);
    }
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 250));
  }
  fail(`${name} did not become ready at ${url}: ${lastFailure}`);
}

async function startLocal() {
  verifyNodeVersion();
  loadLocalEnvironment();
  ensurePythonEnvironment();
  if (!existsSync(viteEntry)) {
    fail("Node dependencies are missing. Run npm run setup:local first.");
  }
  const configuration = localConfiguration();
  await preflightPorts(configuration);
  const commonEnvironment = {
    ...process.env,
    CYBERMENTOR_LOCAL_HOST: configuration.host,
    CYBERMENTOR_WEB_PORT: String(configuration.webPort),
    CYBERMENTOR_TRUSTED_API_PORT: String(configuration.trustedPort),
    CYBERMENTOR_LEGACY_API_PORT: String(configuration.legacyPort),
    CYBERMENTOR_TRUSTED_API_ORIGIN: `http://${configuration.host}:${configuration.trustedPort}`,
    CYBERMENTOR_LEGACY_API_ORIGIN: `http://${configuration.host}:${configuration.legacyPort}`,
  };
  const definitions = [
    {
      name: "trusted",
      command: venvPython,
      args: [
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        configuration.host,
        "--port",
        String(configuration.trustedPort),
      ],
      cwd: backend,
      env: {
        ...commonEnvironment,
        ...trustedEnvironment(configuration),
      },
    },
    {
      name: "content",
      command: process.execPath,
      args: [resolve(root, "server", "server.mjs"), "--api-only"],
      cwd: root,
      env: {
        ...commonEnvironment,
        HOST: configuration.host,
        PORT: String(configuration.legacyPort),
      },
    },
    {
      name: "web",
      command: process.execPath,
      args: [
        viteEntry,
        "--host",
        configuration.host,
        "--port",
        String(configuration.webPort),
        "--strictPort",
      ],
      cwd: root,
      env: commonEnvironment,
    },
  ];
  let shuttingDown = false;
  const children = definitions.map((definition) => {
    const child = spawn(definition.command, definition.args, {
      cwd: definition.cwd,
      env: definition.env,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });
    prefixOutput(child.stdout, definition.name, process.stdout);
    prefixOutput(child.stderr, definition.name, process.stderr);
    return { name: definition.name, child };
  });

  const shutdown = (exitCode = 0) => {
    if (shuttingDown) return;
    shuttingDown = true;
    process.stdout.write("\nStopping CyberMentor local services...\n");
    for (const { child } of children) stopProcessTree(child);
    process.exitCode = exitCode;
  };

  for (const { name, child } of children) {
    child.once("error", (error) => {
      if (!shuttingDown) {
        process.stderr.write(`[${name}] failed to start: ${error.message}\n`);
        shutdown(1);
      }
    });
    child.once("exit", (code) => {
      if (!shuttingDown) {
        process.stderr.write(
          `[${name}] stopped unexpectedly with code ${code ?? "unknown"}.\n`,
        );
        shutdown(code || 1);
      }
    });
  }
  process.once("SIGINT", () => shutdown(0));
  process.once("SIGTERM", () => shutdown(0));

  try {
    await waitFor(
      "Trusted API",
      `http://${configuration.host}:${configuration.trustedPort}/readyz`,
      children,
    );
    await waitFor(
      "Content API",
      `http://${configuration.host}:${configuration.legacyPort}/readyz`,
      children,
    );
    await waitFor(
      "Frontend",
      `http://${configuration.host}:${configuration.webPort}/`,
      children,
    );
  } catch (error) {
    process.stderr.write(
      `${error instanceof Error ? error.message : String(error)}\n`,
    );
    shutdown(1);
    return;
  }

  process.stdout.write(
    [
      "",
      "CyberMentor local development is ready:",
      `  Learner interface  http://${configuration.host}:${configuration.webPort}`,
      `  Trusted API       http://${configuration.host}:${configuration.trustedPort}`,
      `  Content API       http://${configuration.host}:${configuration.legacyPort}`,
      "  Email             verification/reset links appear in [trusted] console output",
      "Press Ctrl+C once to stop every service.",
      "",
    ].join("\n"),
  );
}

async function main() {
  const command = process.argv[2];
  if (command === "setup") {
    prepareLocal({ fullSetup: true });
    return;
  }
  if (command === "prepare") {
    prepareLocal();
    return;
  }
  if (command === "start") {
    await startLocal();
    return;
  }
  fail("Usage: node scripts/local-dev.mjs <setup|prepare|start>");
}

main().catch((error) => {
  process.stderr.write(
    `CyberMentor local startup failed: ${error instanceof Error ? error.message : String(error)}\n`,
  );
  process.exitCode = 1;
});
