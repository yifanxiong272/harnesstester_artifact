import assert from "node:assert/strict";

/** Adapt only unused formal parameters/call arguments for syntax comparisons. */
export function withoutUnusedArguments(ts, source) {
  const signatures = {
    seedFunctionParamDeps: [1, "info ctx"],
    stableClassName: [1, "ts sourceFile node"],
    hasModifier: [0, "ts node kind"],
    providerValueKind: [5, "ts expr ctx facts index sourceRules"],
    transportMatchesBoundary: [3, "ts call ctx facts index boundary"],
    transportMatchesCall: [3, "ts call ctx facts index transport"],
    resolveConstructor: [3, "ts call ctx facts index"],
    nodeSpan: [0, "ts sourceFile node"],
    spanOf: [0, "ts sourceFile node"],
    buildInterfaceInfo: [0, "ts file state node"],
    buildTypeAliasInfo: [0, "ts file state node"],
  };
  const reference = (node) => ts.isIdentifier(node)
    || node.kind === ts.SyntaxKind.ThisKeyword
    || (ts.isPropertyAccessExpression(node) && reference(node.expression));
  function visit(node) {
    const declaration = ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node);
    const call = ts.isCallExpression(node);
    const name = declaration ? node.name?.text
      : call ? node.expression.name?.text || node.expression.text : null;
    const signature = Object.hasOwn(signatures, name) ? signatures[name] : null;
    if (signature) {
      const [index, parameters] = signature;
      const expected = parameters.split(" ");
      if (declaration) {
        assert.deepEqual(node.parameters.map((parameter) => parameter.name.text), expected, name);
        node.parameters = ts.factory.createNodeArray(node.parameters.filter((_, i) => i !== index));
      } else {
        assert.equal(node.arguments.length, expected.length, name);
        assert.ok(reference(node.arguments[index]), `${name}: expected a simple argument reference`);
        node.arguments = ts.factory.createNodeArray(node.arguments.filter((_, i) => i !== index));
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
  return source;
}

/** Omit only the formal extractor's retired scheduling diagnostics. */
export function regionPayload(payload) {
  const { analyzed_functions, max_batch_size, dirty_refs, iteration_stats, ...fixed_point } = payload.fixed_point;
  return { ...payload, fixed_point };
}

export function formalFactState(store) {
  return {
    ...store,
    changedRefs: new Map([...store.changedRefs].map(([key, entry]) => [key, entry.ref])),
  };
}

/** Observe scheduling without replacing any transfer or worklist operation. */
export function analyzedRun(Analyzer, input) {
  const analyzer = new Analyzer(input);
  const events = [];
  for (const name of ["seedModuleBodyFacts", "seedClassBodyFacts", "analyzeFunction"]) {
    const operation = analyzer[name];
    analyzer[name] = function (...args) {
      events.push([name, ...args.map(arg => arg.key)]);
      return operation.apply(this, args);
    };
  }
  const enqueue = analyzer.enqueueChangedRefs;
  analyzer.enqueueChangedRefs = function (queue, options = {}) {
    const result = enqueue.call(this, queue, options);
    events.push(["queue", options.ignoreLocalFunction ?? null, [...queue.pending]]);
    return result;
  };
  // Ref reads drive re-analysis; preserve their order as well as final facts.
  const read = analyzer.recordRefRead;
  analyzer.recordRefRead = function (ref, functionId) {
    events.push(["read", structuredClone(ref), functionId]);
    return read.call(this, ref, functionId);
  };
  return { payload: analyzer.analyzeProject(), events, facts: { ...analyzer.facts } };
}
