#!/usr/bin/env node
/** Build frontend for Tauri with VITE_PUBLIC_CLOUD_URL from infrastructure/public-url.env */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const frontendDir = path.join(root, "frontend");

const result = spawnSync(
  process.platform === "win32" ? "python" : "python3",
  [path.join(root, "scripts", "public_url_config.py"), "--api-url"],
  { encoding: "utf-8", cwd: root }
);

const apiUrl = (result.stdout || "").trim() || "http://88.222.220.238:8010/api/v1";
console.log(`Building frontend with VITE_PUBLIC_CLOUD_URL=${apiUrl}`);

const npm = process.platform === "win32" ? "npm" : "npm";
const build = spawnSync(npm, ["run", "build"], {
  cwd: frontendDir,
  stdio: "inherit",
  shell: process.platform === "win32",
  env: { ...process.env, VITE_PUBLIC_CLOUD_URL: apiUrl },
});

process.exit(build.status ?? 1);
