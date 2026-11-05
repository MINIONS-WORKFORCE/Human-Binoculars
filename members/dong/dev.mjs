import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { loadEnvFile } from "node:process";

const root = fileURLToPath(new URL("../../", import.meta.url));
const python = resolve(
  root,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);

if (!existsSync(python)) {
  console.error("Missing .venv. Follow the Python setup in the root README first.");
  process.exit(1);
}

try {
  loadEnvFile(resolve(root, ".env"));
} catch {
  console.error("Could not load .env. Copy .env.example to .env in the repo root.");
  process.exit(1);
}

const host = process.env.API_HOST?.trim();
const portText = process.env.API_PORT?.trim();
const port = Number(portText);
if (!host || !/^\d+$/.test(portText ?? "") || port < 1 || port > 65535) {
  console.error("Set API_HOST and an integer API_PORT between 1 and 65535 in .env.");
  process.exit(1);
}

const result = spawnSync(
  python,
  [
    "-m",
    "uvicorn",
    "main:app",
    "--app-dir",
    "members/dong",
    "--reload",
    "--host",
    host,
    "--port",
    String(port),
    ...process.argv.slice(2),
  ],
  { cwd: root, stdio: "inherit" },
);

if (result.error) {
  console.error(`Could not start the backend: ${result.error.message}`);
}
process.exit(result.status ?? 1);
