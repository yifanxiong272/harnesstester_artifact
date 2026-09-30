import fs from "node:fs";
import path from "node:path";
import { compareSpans, spanKey } from "./models.mjs";

/** Build a stable identity for one emitted location. */
export function locationKey(location) {
  return `${location.filepath}:${location.start_line}:${location.end_line}`;
}

/** Remove duplicate locations and sort them for deterministic artifacts. */
export function dedupeLocations(locations) {
  const seen = new Set();
  const out = [];
  for (const location of locations) {
    const key = locationKey(location);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(location);
  }
  return out.sort(
    (left, right) =>
      left.filepath.localeCompare(right.filepath) ||
      left.start_line - right.start_line ||
      left.end_line - right.end_line,
  );
}

/** Build a deduplicated, sorted location payload with its measurement unit. */
export function buildLocationPayload({ unit, locations }) {
  return {
    unit,
    locations: dedupeLocations(locations),
  };
}

/** Collect source, data-dependence, and optional control-dependence locations. */
export function buildCompactFactLocationPayload(payload, options = {}) {
  return buildLocationPayload({
    unit: "ts_line_range",
    locations: [
      ...locationList(payload.sources),
      ...locationList(payload.data_dependence),
      ...(options.includeControlDependence ? locationList(payload.control_dependence) : []),
    ],
  });
}

/** Convert an internal fact-store span to the public location shape. */
export function spanLocation(span) {
  return {
    filepath: span.filepath,
    start_line: span.start_line,
    end_line: span.end_line,
  };
}

/** Extract public locations from payload entries that own a location field. */
function locationList(entries = []) {
  return entries.map((entry) => entry.location).filter(Boolean);
}

/** Convert a function identity to the public control-region shape. */
export function functionLocation(info) {
  return {
    filepath: info.file,
    function: info.qualname || info.name || info.key,
    start_line: info.start,
    end_line: info.end,
  };
}

/** Serialize provider/model source statement locations from a FactStore. */
export function sourcePayloads(facts) {
  return [...facts.sources.values()]
    .sort(compareSpans)
    .map((span) => ({ location: spanLocation(span) }));
}

/** Serialize grouped data-flow edges from a FactStore. */
export function dataEdgePayloads(facts) {
  const grouped = new Map();
  const spans = new Map();
  for (const edge of closureDataEdges(facts).sort((left, right) => {
    return (
      compareSpans(left.span, right.span) ||
      left.dependence_type.localeCompare(right.dependence_type)
    );
  })) {
    const key = spanKey(edge.span);
    const sourceSpans = edge.source_spans.filter((sourceSpan) => spanKey(sourceSpan) !== key);
    if (!sourceSpans.length) continue;
    if (!grouped.has(key)) grouped.set(key, new Map());
    if (!grouped.get(key).has(edge.dependence_type)) {
      grouped.get(key).set(edge.dependence_type, new Map());
    }
    for (const sourceSpan of sourceSpans) {
      grouped.get(key).get(edge.dependence_type).set(spanKey(sourceSpan), sourceSpan);
    }
    spans.set(key, edge.span);
  }

  for (const [key] of facts.attemptedDataRegions || []) {
    if (facts.sources.has(key) || grouped.has(key)) continue;
    throw new Error(`LLM-dependent flow graph has a non-source region without concrete flow: ${key}`);
  }

  return [...grouped.keys()].sort((left, right) => compareSpans(spans.get(left), spans.get(right)))
    .map((key) => ({
      location: spanLocation(spans.get(key)),
      flows: [...grouped.get(key)].sort(([left], [right]) => left.localeCompare(right))
        .map(([dependenceType, sources]) => ({
          dependence_type: dependenceType,
          source_locations: [...sources.values()].sort(compareSpans).map(spanLocation),
        })),
    }));
}

/** Add only bridge candidates required to make predecessor locations concrete nodes. */
function closureDataEdges(facts) {
  const edges = [...facts.dataEdges.values()];
  const destinations = new Set(edges.map((edge) => spanKey(edge.span)));
  const predecessors = new Set(edges.flatMap((edge) => edge.source_spans.map(spanKey)));
  const sourceKeys = new Set(facts.sources.keys());
  const bridgesByDestination = new Map();
  for (const edge of facts.bridgeEdges.values()) {
    const key = spanKey(edge.span);
    if (!bridgesByDestination.has(key)) bridgesByDestination.set(key, []);
    bridgesByDestination.get(key).push(edge);
  }

  while (true) {
    const missing = [...predecessors]
      .filter((key) => !sourceKeys.has(key) && !destinations.has(key))
      .sort();
    if (!missing.length) return edges;

    let added = false;
    for (const key of missing) {
      for (const edge of bridgesByDestination.get(key) || []) {
        edges.push(edge);
        destinations.add(key);
        for (const sourceSpan of edge.source_spans) predecessors.add(spanKey(sourceSpan));
        added = true;
      }
    }
    if (!added) {
      throw new Error(`LLM-dependent flow graph is not source-closed: ${missing.join(", ")}`);
    }
  }
}

/** Serialize function-level control-dependence regions. */
export function controlRegionPayload(region) {
  return {
    location: functionLocation(region.info),
    control_flow_statement_location: spanLocation(region.control_span),
  };
}

/** Serialize source/data/control facts and fixed-point convergence metadata. */
export function buildFactPayload({
  project,
  facts,
  controlRegions = [],
  stats,
  options,
}) {
  const fixedPoint = {
    converged: Boolean(stats.converged),
    iterations: stats.iterations,
    max_iterations: stats.maxIterations ?? stats.max_iterations,
  };
  return {
    project,
    extractor: "source_rooted_cross_function_return_flow",
    options: {
      control_dependence_mode: options.controlDependenceMode || options.control_dependence_mode,
    },
    fixed_point: fixedPoint,
    sources: sourcePayloads(facts),
    data_dependence: dataEdgePayloads(facts),
    control_dependence: [...controlRegions]
      .sort((left, right) =>
        left.info.file.localeCompare(right.info.file) ||
        (left.info.qualname || "").localeCompare(right.info.qualname || "") ||
        compareSpans(left.control_span, right.control_span),
      )
      .map(controlRegionPayload),
  };
}

/** Write one compact JSON workflow artifact. */
export function writeJson(pathValue, payload) {
  const out = path.resolve(pathValue);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, `${JSON.stringify(payload, null, 2)}\n`);
  console.log(`wrote ${out}`);
}
