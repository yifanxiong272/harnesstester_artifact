/** Prepare native Vitest configuration, environment, and sandbox rules. */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { ensureDir } from "../support/json.mjs";
import { normalizePath } from "../support/path_safety.mjs";

export function configuredCommand(testCommand, testFile) {
  const command = (
    testCommand || ["pnpm", "exec", "vitest", "run", "<generated-test-file>"]
  ).map((part) => (part === "<generated-test-file>" ? testFile : part));
  if (!command.includes(testFile)) {
    command.push(testFile);
  }
  return command;
}

export function resolveLocalLauncher(command, projectRoot) {
  if (
    path.basename(command[0] || "") === "pnpm" &&
    command[1] === "exec" &&
    command[2] === "vitest"
  ) {
    const candidates = [
      path.join(projectRoot, "node_modules", ".bin", "vitest"),
    ];
    const configuredRoot = rootFlagValue(command);
    if (configuredRoot) {
      candidates.push(
        path.join(
          resolveProjectPath(projectRoot, configuredRoot),
          "node_modules",
          ".bin",
          "vitest",
        ),
      );
    }
    for (const localVitest of candidates) {
      if (fs.existsSync(localVitest)) {
        return [localVitest, ...command.slice(3)];
      }
    }
  }
  return command;
}

const VALIDATION_ENV_KEYS = new Set([
  "PATH",
  "SHELL",
  "TERM",
  "LANG",
  "LC_ALL",
  "TZ",
]);

function resolveProjectPath(projectRoot, value) {
  return path.isAbsolute(value) ? value : path.resolve(projectRoot, value);
}

function configFlagIndex(command) {
  return command.findIndex((part) => part === "--config" || part === "-c");
}

function rootFlagValue(command) {
  let value = "";
  for (let index = 0; index < command.length; index += 1) {
    const part = command[index];
    if (part === "--") break;
    if ((part === "--root" || part === "-r") && command[index + 1]) {
      value = command[++index];
    } else if (part.startsWith("--root=")) {
      value = part.slice("--root=".length);
    }
  }
  return value;
}

function effectiveVitestRoot(command, projectRoot) {
  const configuredRoot = rootFlagValue(command);
  return configuredRoot
    ? resolveProjectPath(projectRoot, configuredRoot)
    : projectRoot;
}

function defaultVitestConfig(command, projectRoot) {
  const root = effectiveVitestRoot(command, projectRoot);
  for (const stem of ["vitest.config", "vite.config"]) {
    for (const extension of ["ts", "mts", "cts", "js", "mjs", "cjs"]) {
      const candidate = path.join(root, `${stem}.${extension}`);
      if (fs.existsSync(candidate)) {
        return candidate;
      }
    }
  }
  return "";
}

export function resolvedVitestConfig(
  command,
  projectRoot,
  { discoverDefault = false } = {},
) {
  const index = configFlagIndex(command);
  if (index >= 0 && index + 1 < command.length) {
    return {
      index,
      path: resolveProjectPath(projectRoot, command[index + 1]),
      source: "explicit",
    };
  }
  if (!discoverDefault) {
    return null;
  }
  const configPath = defaultVitestConfig(command, projectRoot);
  return configPath ? { index: -1, path: configPath, source: "default" } : null;
}

export function writeVitestConfigOverride({
  command,
  projectRoot,
  outDir,
  testFile,
  forceExactInclude = false,
}) {
  const resolved = resolvedVitestConfig(command, projectRoot, {
    discoverDefault: forceExactInclude,
  });
  if (!resolved) {
    return { command, override: null, adjustment: null, scratchPaths: [] };
  }
  const originalConfigPath = resolved.path;
  if (!fs.existsSync(originalConfigPath)) {
    const adjustedCommand = [...command];
    if (resolved.index >= 0) {
      adjustedCommand.splice(resolved.index, 2);
    }
    return {
      command: adjustedCommand,
      override: null,
      adjustment: {
        kind: "missing_explicit_config",
        requested_config_path: originalConfigPath,
        effective: "vitest_default_discovery",
      },
      scratchPaths: [],
    };
  }
  const generatedConfigPath = path.join(
    outDir,
    forceExactInclude
      ? "vitest.collection-retry.config.mjs"
      : "vitest.validation.config.mjs",
  );
  const viteCacheDir = path.join(outDir, "vite-cache");
  const vitestCacheDir = path.join(outDir, "vitest-cache");
  const fsModuleCachePath = path.join(outDir, "vitest-fs-module-cache");
  const configuredRoot = rootFlagValue(command);
  const targetPath = path.resolve(projectRoot, testFile);
  ensureDir(viteCacheDir);
  ensureDir(vitestCacheDir);
  ensureDir(fsModuleCachePath);
  const include = forceExactInclude
    ? `      include: [path.relative(root, ${JSON.stringify(targetPath)}).split(path.sep).join("/")],\n      exclude: [],\n`
    : "";
  const loaderIndex = command.indexOf("--configLoader");
  const bundled = command.includes("--configLoader=bundle") ||
    (loaderIndex >= 0 && command[loaderIndex + 1] === "bundle");
  // Older Vite bundlers externalize file URLs, leaving TS configs untranspiled.
  const configImport = bundled
    ? normalizePath(originalConfigPath)
    : pathToFileURL(originalConfigPath).href;
  fs.writeFileSync(
    generatedConfigPath,
    `import baseConfig from ${JSON.stringify(configImport)};
import path from "node:path";

export default async function validationConfig(env) {
  const loaded = typeof baseConfig === "function" ? await baseConfig(env) : await baseConfig;
  const config = loaded && typeof loaded === "object" ? loaded : {};
  const test = config.test && typeof config.test === "object" ? config.test : {};
  const root = path.resolve(${JSON.stringify(path.resolve(projectRoot))}, ${JSON.stringify(configuredRoot)} || test.root || config.root || ".");
  const cache = test.cache && typeof test.cache === "object" ? test.cache : {};
  const experimental = test.experimental && typeof test.experimental === "object" ? test.experimental : {};
  return {
    ...config,
    root,
    cacheDir: ${JSON.stringify(viteCacheDir)},
    test: {
      ...test,
      ...(test.root === undefined ? {} : { root }),
${include}      cache: {
        ...cache,
        dir: ${JSON.stringify(vitestCacheDir)},
      },
      experimental: {
        ...experimental,
        fsModuleCachePath: ${JSON.stringify(fsModuleCachePath)},
      },
    },
  };
}
`,
  );
  const wrappedCommand = [...command];
  if (resolved.index >= 0) {
    wrappedCommand[resolved.index + 1] = generatedConfigPath;
  } else {
    const testIndex = wrappedCommand.indexOf(testFile);
    wrappedCommand.splice(
      testIndex >= 0 ? testIndex : wrappedCommand.length,
      0,
      "--config",
      generatedConfigPath,
    );
  }
  return {
    command: wrappedCommand,
    override: {
      original_config_path: originalConfigPath,
      generated_config_path: generatedConfigPath,
      config_source: resolved.source,
      force_exact_include: forceExactInclude,
      // The base config can be async; the actual relative glob is resolved in Vitest.
      exact_include: forceExactInclude ? null : "",
      ...(forceExactInclude ? { exact_include_target: targetPath } : {}),
      vite_cache_dir: viteCacheDir,
      vitest_cache_dir: vitestCacheDir,
      fs_module_cache_path: fsModuleCachePath,
    },
    adjustment: null,
    scratchPaths: [viteCacheDir, vitestCacheDir, fsModuleCachePath],
  };
}

export function ensureProjectEnv(outDir, baseEnv) {
  const env = Object.fromEntries(
    Object.entries(baseEnv).filter(([key]) => VALIDATION_ENV_KEYS.has(key)),
  );
  const homeDir = path.join(outDir, "home");
  const tmpDir = path.join(outDir, "tmp");
  ensureDir(homeDir);
  ensureDir(tmpDir);
  env.HOME = homeDir;
  env.TMPDIR = tmpDir;
  env.CI = "true";
  env.NO_COLOR = "1";
  return { env, scratchPaths: [homeDir, tmpDir] };
}

function sandboxPath(value) {
  const resolved = path.resolve(value);
  const canonical = fs.existsSync(resolved)
    ? fs.realpathSync.native(resolved)
    : resolved;
  return JSON.stringify(canonical);
}

function sandboxAncestorRules(paths) {
  const home = path.resolve(os.homedir());
  const traversal = new Set([home]);
  const packages = new Set();
  for (const value of paths) {
    let current = path.resolve(value);
    while (current.startsWith(`${home}${path.sep}`)) {
      packages.add(path.join(current, "package.json"));
      current = path.dirname(current);
      traversal.add(current);
    }
  }
  const rules = (paths, operation) =>
    [...paths]
      .sort((left, right) => left.length - right.length)
      .map((value) => `(allow ${operation} (literal ${sandboxPath(value)}))`);
  return [
    ...rules(traversal, "file-read-metadata"),
    ...rules(packages, "file-read*"),
  ];
}

export function sandboxedCommand(command, { projectRoot, outDir, testFile }) {
  const sandboxExec = "/usr/bin/sandbox-exec";
  if (process.platform !== "darwin" || !fs.existsSync(sandboxExec)) {
    return { command, network_sandboxed: false, filesystem_sandboxed: false };
  }
  const nodeModules = path.join(projectRoot, "node_modules");
  const runtimeRoot = fs.existsSync(nodeModules)
    ? path.dirname(fs.realpathSync(nodeModules))
    : projectRoot;
  const localNode = path.join(nodeModules, ".bin", "node");
  const nodePaths = fs.existsSync(localNode)
    ? [fs.realpathSync(localNode)]
    : [];
  const nodeLib = nodePaths.length
    ? path.resolve(path.dirname(nodePaths[0]), "../lib")
    : null;
  const generatedTestDir = path.dirname(path.resolve(projectRoot, testFile));
  const profile = [
    "(version 1)",
    "(allow default)",
    "(deny network*)",
    "(deny file-write*)",
    `(deny file-read* (subpath ${sandboxPath(os.homedir())}))`,
    ...sandboxAncestorRules([projectRoot, runtimeRoot, outDir, ...nodePaths]),
    ...nodePaths.map((file) => `(allow file-read* (literal ${sandboxPath(file)}))`),
    ...(nodeLib ? [`(allow file-read* (subpath ${sandboxPath(nodeLib)}))`] : []),
    `(allow file-read* (subpath ${sandboxPath(projectRoot)}))`,
    `(allow file-read* (subpath ${sandboxPath(runtimeRoot)}))`,
    `(allow file-read* (subpath ${sandboxPath(outDir)}))`,
    `(allow file-write* (subpath ${sandboxPath(generatedTestDir)}))`,
    `(allow file-write* (subpath ${sandboxPath(outDir)}))`,
    `(allow file-write* (literal ${sandboxPath("/dev/null")}))`,
  ].join(" ");
  return {
    command: [sandboxExec, "-p", profile, ...command],
    network_sandboxed: true,
    filesystem_sandboxed: true,
  };
}
