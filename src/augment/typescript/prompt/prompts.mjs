import fs from "node:fs";
import path from "node:path";

import { exportSurfaceForFile, projectSourceFile } from "./context.mjs";
import { DEFAULT_STRATEGY, isContractDirected } from "../strategy.mjs";
import {
  TOP_LEVEL_SUITE_ID,
  targetBinding,
  targetLoader,
  targetBindingsForSeed,
  testSuites,
  vitestNamespace,
} from "../test_seed.mjs";
import { parseProjectFile } from "../typescript_ast.mjs";

function numberedExcerpt(filepath, lines, startLine, endLine) {
  const start = Math.max(1, startLine);
  const end = Math.min(lines.length, endLine);
  return {
    path: filepath,
    start_line: start,
    end_line: end,
    code_excerpt: lines
      .slice(start - 1, end)
      .map(
        (line, index) => `${String(start + index).padStart(5, " ")} | ${line}`,
      )
      .join("\n"),
  };
}

function sourceContext(projectRoot, objective) {
  const source = projectSourceFile(projectRoot, objective.filepath);
  if (source.status !== "found") {
    throw new Error(`source context is unavailable: ${objective.filepath}`);
  }
  const text = fs.readFileSync(source.file, "utf8");
  const lines = text.split("\n");
  return [
    numberedExcerpt(
      objective.filepath,
      lines,
      objective.start_line,
      objective.end_line,
    ),
  ];
}

function generatedTestSpecifier(sourceFile, generatedTestFile, specifier) {
  if (!specifier.startsWith(".")) return specifier;
  const dependency = path.posix.normalize(
    path.posix.join(path.posix.dirname(sourceFile), specifier),
  );
  const relative = path.posix.relative(
    path.posix.dirname(generatedTestFile),
    dependency,
  );
  return relative.startsWith(".") ? relative : `./${relative}`;
}

function sourceMetadata(projectRoot, objective, generatedTestFile, compiler) {
  const { typescript, sourceFile } = parseProjectFile(
    projectRoot,
    objective.filepath,
    compiler,
  );
  const imports = sourceFile.statements
    .filter((statement) => typescript.isImportDeclaration(statement))
    .map((statement) => {
      const specifier = statement.moduleSpecifier.text;
      return {
        source_specifier: specifier,
        generated_test_specifier: generatedTestSpecifier(
          objective.filepath,
          generatedTestFile,
          specifier,
        ),
      };
    });
  return {
    imports,
    exports: exportSurfaceForFile(projectRoot, objective.filepath, typescript),
  };
}

function seedTestContext(projectRoot, seedTest, targetFile, typescript) {
  const filepath = String(seedTest?.test_file ?? "");
  const source = projectSourceFile(projectRoot, filepath);
  if (source.status !== "found") {
    throw new Error(`seed test context is unavailable: ${filepath}`);
  }
  const content = fs.readFileSync(source.file, "utf8");
  const suites = testSuites(typescript, filepath, content).map((suite) => ({
    suite_id: suite.suite_id,
    title: suite.title,
    start_line: suite.start_line,
    end_line: suite.end_line,
  }));
  return {
    path: filepath,
    start_line: 1,
    end_line: Math.max(1, content.split(/\r?\n/u).length),
    content,
    reverse_coverage_score: Number(seedTest.score ?? 0),
    target_bindings: targetBindingsForSeed(
      typescript,
      filepath,
      targetFile,
      content,
    ),
    suites:
      suites.length > 0
        ? suites
        : [
            {
              suite_id: TOP_LEVEL_SUITE_ID,
              title: "",
              start_line: 1,
              end_line: Math.max(1, content.split(/\r?\n/u).length),
            },
          ],
  };
}

export function buildCoverageTargetPacket(context) {
  const objective = context.objective;
  const namespace = vitestNamespace(objective.seed_test);
  const loader = targetLoader(objective.seed_test, context.targetModuleImport);
  const binding = targetBinding(objective.seed_test, context.targetModuleImport);
  const metadata = sourceMetadata(
    context.currentRoot,
    objective,
    context.generatedTestPreview,
    context.typescript,
  );
  return {
    project: context.project,
    iteration: context.iteration,
    test_name_suffix:
      context.testNameSuffix ??
      `_round_${String(context.iteration).padStart(3, "0")}`,
    objective: {
      objective_id: objective.objective_id,
      filepath: objective.filepath,
      start_line: objective.start_line,
      end_line: objective.end_line,
      round_missing_lines: context.targetCoverage.uncovered_lines,
      round_missing_branches: context.targetBranchGaps,
    },
    source_context: sourceContext(context.currentRoot, objective),
    source_imports: metadata.imports,
    export_surface: metadata.exports,
    seed_test: seedTestContext(
      context.currentRoot,
      objective.seed_test,
      objective.filepath,
      context.typescript,
    ),
    output_contract: {
      generated_test_directory: path.posix.dirname(
        context.generatedTestPreview,
      ),
      vitest_namespace: namespace,
      target_binding: binding,
      target_loader: loader,
    },
  };
}

export function coverageContinuationMessage({
  acceptedTestNames,
  contextRequestAvailable,
  pass,
  targetCoverage,
  targetBranchGaps,
  testNameSuffix,
  strategy = DEFAULT_STRATEGY,
}) {
  const directed = isContractDirected(strategy);
  const contextInstruction =
    directed && contextRequestAvailable
      ? "One deterministic context request batch remains available."
      : "Do not request more context.";
  return [
    "Continue coverage-guided augmentation for the same source file and seed harness.",
    "Do not repeat accepted tests. First cover source behavior families that no accepted test exercises; only then add another variant of an already covered behavior. Propose independent tests for distinct behaviors or outcomes among the remaining ordinary coverage gaps. Return four units when at least four distinct remaining behaviors are testable; otherwise return one unit per testable behavior, up to four.",
    contextInstruction,
    directed
      ? "Return the same request_context or propose_test JSON contract used above. Every new static test name must end with the new test_name_suffix."
      : "Return the same propose_test JSON contract used above. Every new static test name must end with the new test_name_suffix.",
    JSON.stringify(
      {
        pass,
        test_name_suffix: testNameSuffix,
        accepted_test_names: acceptedTestNames,
        remaining_uncovered_lines: targetCoverage.uncovered_lines,
        remaining_uncovered_branches: targetBranchGaps,
      },
      null,
      2,
    ),
  ].join("\n\n");
}

export function renderCoverageTargetPrompt(
  packet,
  strategy = DEFAULT_STRATEGY,
) {
  const directed = isContractDirected(strategy);
  return [
    "Generate deterministic TypeScript/Vitest tests that increase coverage of the selected source file.",
    "",
    "The packet contains ordinary coverage facts for the selected source file." +
      (directed
        ? " Prioritize behavior directly or indirectly influenced by model-derived values, including structured provider or tool payloads, accumulated agent state, observations, and runtime or error signals."
        : ""),
    "",
    "Before proposing code, identify the diverse behavior cases needed to exercise the remaining gaps across the file. Distribute test units across different source behavior families before adding normal, boundary, or error variants of the same behavior. Each unit must cover a distinct behavior or outcome and assert behavior-specific outputs or side effects.",
    "",
    (directed
      ? "When relevant, preserve provider, tool, action, message, and observation payload shapes; construct required state or history; match sync/async signatures and return shapes; patch the symbol resolved by the code under test; and assert observable behavior. "
      : "Assert observable behavior. ") +
      "Do not use live models, networks, external services, or real API keys.",
    "",
    "Extend the provided seed test harness without modifying the original file. Choose exactly one suite_id listed in seed_test.suites; generated units are inserted at the end of that suite so they can reuse its lexical fixtures, hooks, helpers, imports, and mocks. Existing seed test registrations are omitted from each generated sibling, so append_code must not depend on state created inside an existing test callback. Access only target names listed in export_surface.exports; other declarations visible in source_context may be private." +
      (directed
        ? " If an exact constructor, fixture, collaborator, export, or mock contract is missing, return one context request batch. Otherwise propose tests directly."
        : " Propose tests directly."),
    "",
    `Every generated test name must be a static string ending with the packet's test_name_suffix. Each test_units entry is inserted verbatim into an isolated seed-derived harness and must contain exactly one new test call. Use ${packet.output_contract.vitest_namespace}.it or ${packet.output_contract.vitest_namespace}.test and the same namespace for expect, vi, and other Vitest APIs. Do not import Vitest or redeclare seed bindings. Return four independent units when at least four distinct behaviors are testable; otherwise return one unit per testable behavior, up to four.`,
    `Prefer seed_test.target_bindings and the seed's existing helpers when its current mocks already expose the required behavior. Otherwise use ${packet.output_contract.target_binding} to access target exports through an injected static namespace. If the test needs a new dependency mock or must bypass a seed mock of the target, do not use that static namespace: register the mock, then destructure exports directly from the module namespace returned by await ${packet.output_contract.target_loader}(), for example const { exportedName } = await ${packet.output_contract.target_loader}();. The loader does not return an object with an exports property. Choose exactly one target-access path per test. Do not add a direct import of the selected source module.`,
    `The generated test is a sibling copy of the seed test, so its relative imports resolve from the same directory. source_imports gives the exact generated_test_specifier for every source dependency. Each append_code must be exactly one top-level it/test registration; place all fixtures, helpers, and ${packet.output_contract.vitest_namespace}.vi.doMock(specifier, factory) calls inside that test callback before the target loader. Never call ${packet.output_contract.vitest_namespace}.doMock or add hoisted mock calls.`,
    "",
    ...(directed
      ? [
          "Return only one JSON object. Context may be requested once:",
          JSON.stringify(
            {
              action: "request_context",
              requests: [
                {
                  kind: "export_surface|module_context|symbol_definition|function_definition|class_definition|test_file_context",
                  filepath: "project/relative/path.ts",
                  qualname: "exact.qualified.name",
                  start_line: 1,
                  end_line: 20,
                  reason: "contract required by the test",
                },
              ],
            },
            null,
            2,
          ),
          "",
          "Or return a proposal:",
        ]
      : ["Return only one JSON object:"]),
    JSON.stringify(
      {
        action: "propose_test",
        rationale: "brief factual rationale",
        suite_id: packet.seed_test.suites[0].suite_id,
        test_units: [
          {
            label: "stable-label",
            append_code: `${packet.output_contract.vitest_namespace}.it("behavior${packet.test_name_suffix}", async () => { ${packet.output_contract.vitest_namespace}.expect(true).toBe(true); });`,
            targeted_objective_ids: [packet.objective.objective_id],
            targeted_lines: ["source.ts:line"],
            targeted_branch_slots: [],
            mocking_strategy: "brief factual description",
            oracle: "observable assertion",
            risk_notes: [],
          },
        ],
      },
      null,
      2,
    ),
    "",
    "Packet:",
    JSON.stringify(packet, null, 2),
  ].join("\n");
}

export function contextReply(records) {
  return [
    "Deterministically resolved project context follows.",
    "Return a propose_test object now; do not request more context.",
    JSON.stringify(records, null, 2),
  ].join("\n");
}

export function repairMessage(
  context,
  row,
  failure,
  traceback,
  contextRequestLimit = 0,
) {
  const directed = isContractDirected(context.strategy);
  if (!directed) contextRequestLimit = 0;
  const generatedDirectory = path.posix.dirname(context.generatedTestPreview);
  const namespace = vitestNamespace(context.objective.seed_test);
  const binding = targetBinding(
    context.objective.seed_test,
    context.targetModuleImport,
  );
  const loader = targetLoader(
    context.objective.seed_test,
    context.targetModuleImport,
  );
  const acceptedTestNames = (row.accepted_units ?? []).map(
    (unit) => unit.test_name,
  );
  const hasRejectedUnits = (row.rejected_units?.length ?? 0) > 0;
  let repairInstruction =
    "The previous candidate was not accepted. Return one complete replacement propose_test object.";
  if (acceptedTestNames.length > 0) {
    repairInstruction = hasRejectedUnits
      ? "Some independent units passed and will be retained. Return replacements only for rejected units; do not repeat accepted tests."
      : "The previous units passed but did not reduce the measured target coverage gaps. Keep them and return additional independent tests for the residual gaps; do not repeat accepted tests.";
  }
  const requestInstruction =
    contextRequestLimit > 0
      ? `If an exact missing contract prevents a sound repair, you may instead return one request_context batch containing at most ${contextRequestLimit} item(s).`
      : "Repair-time context requests are disabled.";
  return [
    `${repairInstruction} First diagnose the root cause from ${directed ? "the measured failure and project frames" : "the measured feedback"}. ${requestInstruction}`,
    directed
      ? "Keep working setup, correct the validation failure or measured file-coverage gap, and preserve exact mock contracts."
      : "Keep working setup and correct the validation failure or measured file-coverage gap.",
    "Access only target names listed in the original packet's export_surface.exports; do not call other declarations that may be private.",
    `The seed remains unchanged. Select one suite_id from the original packet and keep generated units compatible with that suite's lexical setup. Each append_code must be exactly one top-level it/test registration; keep every new fixture, helper, and mock inside its callback. Do not import Vitest or redeclare seed bindings; use ${namespace} for every Vitest API in append_code.`,
    `The generated test is created under ${generatedDirectory}. Prefer the original packet's seed_test.target_bindings and existing seed helpers when their current mocks are sufficient; otherwise use ${binding}. If a new dependency mock is required or a seed target mock must be bypassed, do not use ${binding}: call ${namespace}.vi.doMock(specifier, factory) inside the test callback, then destructure exports directly from await ${loader}(). The loader returns the module namespace itself, not an object with an exports property. Choose exactly one target-access path. Never add a direct target import or call ${namespace}.doMock.`,
    "",
    "Measured feedback:",
    JSON.stringify(
      {
        status: row.status,
        error: row.error ?? "",
        target_coverage_delta: row.target_coverage_delta ?? {},
        round_missing_lines: context.targetCoverage.uncovered_lines,
        round_missing_branches: context.targetBranchGaps,
        accepted_test_names: acceptedTestNames,
        failure_evidence: failure.failure_evidence ?? "",
      },
      null,
      2,
    ),
    ...(directed
      ? [
          "",
          "Project-local traceback context:",
          JSON.stringify(traceback, null, 2),
        ]
      : []),
    "",
    "Return only one JSON object. For a direct repair, use the original propose_test schema and add a top-level diagnosis string.",
    ...(contextRequestLimit > 0
      ? [
          "Or request exact missing context:",
          JSON.stringify(
            {
              action: "request_context",
              diagnosis: "evidence-based root cause and missing contract",
              requests: [
                {
                  kind: "export_surface|module_context|symbol_definition|function_definition|class_definition|test_file_context",
                  filepath: "project/relative/path.ts",
                  qualname: "exact.qualified.name",
                  start_line: 1,
                  end_line: 20,
                  reason: "contract required by the test",
                },
              ],
            },
            null,
            2,
          ),
        ]
      : []),
  ].join("\n");
}
