import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const root = fileURLToPath(new URL("..", import.meta.url));
const python = process.env.XI_PYTHON ?? resolve(root, "backend/.venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const apiPort = process.env.XI_API_PORT ?? "8000";
const webPort = process.env.PORT ?? "3000";
const children = [];
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) child.kill();
  process.exitCode = code;
}
function start(command, args, cwd, env = process.env) {
  const child = spawn(command, args, { cwd, env, stdio: "inherit", windowsHide: true });
  children.push(child);
  child.on("error", error => { console.error(error.message); stop(1); });
  child.on("exit", code => { if (!stopping) stop(code ?? 1); });
}
start(python, ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", apiPort], resolve(root, "backend"));
start(process.execPath, [resolve(root, "node_modules/next/dist/bin/next"), "dev", "--webpack", "--hostname", "127.0.0.1", "--port", webPort], resolve(root, "web"), { ...process.env, XI_BACKEND_ORIGIN: `http://127.0.0.1:${apiPort}` });
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
