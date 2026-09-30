import { returnRef } from "./models.mjs";
import {
  fullNamesForExpression,
  nameIsLocalToFunction,
  refsForPath,
  refsForReadExpr,
  resolveCall,
} from "./resolver.mjs";
import { exprPath } from "./syntax.mjs";
import { unwrapExpression } from "./source_locator.mjs";
import { TYPESCRIPT_PROVIDER_CLIENT_CONSTRUCTORS } from "../source_rules.mjs";

const MODULE_CONST_ALIASES = new WeakMap();

/** Return provider modules if a call is a certified model/provider request.
 *
 * Called by: the FlowAnalyzer before ordinary data propagation for a
 * call/new statement. This is provenance based: direct module calls must resolve
 * through imports, receiver calls require provider facts, and URL sources
 * require standard transports plus endpoint literals. Only transparent,
 * immutable aliases of imported provider callables are accepted; callables
 * propagated through project parameters, fields, or returns are not source
 * evidence because they may be replaced at runtime.
 */
export function providerRequestCall(ts, call, ctx, facts, index, sourceRules) {
  if (!call || (!ts.isCallExpression(call) && !ts.isNewExpression(call))) return new Set();
  const providers = new Set();
  const callee = call.expression;

  for (const fullName of fullNamesForExpression(ts, callee, ctx, index)) {
    const direct = certifiedProviderModuleCall(fullName, sourceRules);
    if (direct) providers.add(direct.provider_module);
  }
  if (providers.size) return providers;

  for (const fullName of moduleConstAliasFullNames(ts, callee, ctx, index)) {
    const direct = certifiedProviderModuleCall(fullName, sourceRules);
    if (direct) providers.add(direct.provider_module);
  }
  if (providers.size) return providers;

  for (const provider of providerRequestFromPath(ts, call, ctx, facts, index, sourceRules)) providers.add(provider);
  for (const provider of providerRequestFromConstructorChain(ts, call, ctx, facts, index, sourceRules)) {
    providers.add(provider);
  }
  for (const provider of transportRequestCall(ts, call, ctx, facts, index, sourceRules)) providers.add(provider);
  return providers;
}

/** Resolve a module-level `const alias = importedProviderCall` callee.
 *
 * This deliberately excludes local aliases, logical/conditional fallbacks,
 * object fields, parameters, and project-call returns. The accepted form has
 * one immutable initializer and therefore denotes the imported callable at
 * every invocation.
 */
function moduleConstAliasFullNames(ts, callee, ctx, index) {
  const node = unwrapExpression(ts, callee);
  if (!node || !ts.isIdentifier(node)) return new Set();
  if (ctx.info.kind !== "module" && nameIsLocalToFunction(node.text, ctx.info, index)) {
    return new Set();
  }

  const sourceFile = ctx.info.sourceFile;
  const moduleScope = index.moduleScopes.get(ctx.info.file);
  if (!sourceFile || !moduleScope) return new Set();
  if (!MODULE_CONST_ALIASES.has(sourceFile)) {
    MODULE_CONST_ALIASES.set(sourceFile, collectModuleConstAliases(ts, sourceFile));
  }
  const alias = MODULE_CONST_ALIASES.get(sourceFile).get(node.text);
  if (!alias) return new Set();
  if (!alias.fullNames) {
    alias.fullNames = fullNamesForExpression(
      ts,
      alias.initializer,
      { ...ctx, info: { ...ctx.info, scope: moduleScope } },
      index,
    );
  }
  return alias.fullNames;
}

/** Collect transparent module-level const aliases once per parsed source file. */
function collectModuleConstAliases(ts, sourceFile) {
  const aliases = new Map();
  for (const statement of sourceFile.statements || []) {
    if (
      !ts.isVariableStatement(statement) ||
      !(statement.declarationList.flags & ts.NodeFlags.Const)
    ) {
      continue;
    }
    for (const declaration of statement.declarationList.declarations || []) {
      if (!ts.isIdentifier(declaration.name)) continue;
      const initializer = unwrapExpression(ts, declaration.initializer);
      if (isTransparentCallableAlias(ts, initializer)) {
        aliases.set(declaration.name.text, { initializer, fullNames: null });
      }
    }
  }
  return aliases;
}

/** Return true only for immutable callable identity expressions. */
function isTransparentCallableAlias(ts, expression) {
  const node = unwrapExpression(ts, expression);
  if (!node) return false;
  if (ts.isIdentifier(node)) return true;
  return (
    ts.isPropertyAccessExpression(node) &&
    isTransparentCallableAlias(ts, node.expression)
  );
}

/** Return providers for artifact downloads whose locator is provider-derived.
 *
 * Called by: the flow analyzer after evaluating call inputs. Artifact download
 * endpoints such as `/files/{id}/content` are not model invocations by
 * themselves; they become LLM-output sources only when the URL/file id was
 * produced by an earlier provider response.
 */
export function providerArtifactDownloadCall(ts, call, ctx, facts, index, sourceRules, urlInfoForExpression) {
  if (!call || (!ts.isCallExpression(call) && !ts.isNewExpression(call))) return new Set();
  const out = new Set();
  const boundaries = endpointBoundaries(sourceRules, { artifact: true }).filter((boundary) =>
    transportMatchesBoundary(ts, call, ctx, index, boundary),
  );
  if (!boundaries.length) return out;
  const urls = endpointUrlCandidates(ts, call, ctx, facts, index, urlInfoForExpression);
  if (!urls.length) return out;
  for (const boundary of boundaries) {
    for (const candidate of urls) {
      if (!endpointMatches(boundary, candidate.text)) continue;
      const candidateInfo = urlInfoForExpression?.(candidate.expression);
      if (!candidateInfo?.origins?.size) continue;
      out.add(boundary.module || boundary.symbol || boundary.boundary_id);
      break;
    }
  }
  return out;
}

/** Return provider kinds produced by reading an expression.
 *
 * Called by: assignment and return transfer. It recognizes provider client
 * constructors, provider-returning project calls, and provider-backed refs.
 */
export function providerValueKind(ts, expr, ctx, facts, index) {
  const out = new Set();
  const node = unwrapExpression(ts, expr);

  if (node && (ts.isCallExpression(node) || ts.isNewExpression(node))) {
    for (const fullName of fullNamesForExpression(ts, node.expression, ctx, index)) {
      const constructor = certifiedProviderClientConstructor(fullName);
      if (constructor) out.add(constructor.provider_module);
    }
    for (const target of resolveCall(ts, node, ctx, facts, index)) {
      for (const provider of facts.providerOf(returnRef(target.key))) out.add(provider);
    }
  }

  for (const ref of refsForReadExpr(ts, node, ctx, facts, index, { includePrefixes: true })) {
    for (const provider of facts.providerOf(ref)) out.add(provider);
  }
  return out;
}

/** Return providers for `client.responses.create()`-style calls.
 *
 * Called by: `providerRequestCall`. It splits the callee path and requires the
 * base receiver path to already carry provider provenance.
 */
export function providerRequestFromPath(ts, call, ctx, facts, index, sourceRules) {
  const path = exprPath(ts, call.expression);
  if (!path) return new Set();
  const parts = path.split(".").filter(Boolean);
  const out = new Set();
  for (let split = 1; split < parts.length; split += 1) {
    const basePath = parts.slice(0, split).join(".");
    const suffix = parts.slice(split).join(".");
    if (!isProviderClientRequestSuffix(suffix, sourceRules)) continue;
    for (const ref of refsForPath(basePath, ctx, facts, index, { includePrefixes: true })) {
      for (const provider of facts.providerOf(ref)) out.add(provider);
    }
  }
  return out;
}

/** Return providers for `new OpenAI().responses.create()`-style chains.
 *
 * Called by: `providerRequestCall`. This avoids trusting receiver names: the
 * base expression itself must resolve to a provider constructor/provider value.
 */
export function providerRequestFromConstructorChain(ts, call, ctx, facts, index, sourceRules) {
  const split = splitMemberBaseAndSuffix(ts, call.expression);
  if (!split || !isProviderClientRequestSuffix(split.suffix.join("."), sourceRules)) return new Set();
  return providerValueKind(ts, split.base, ctx, facts, index);
}

/** Return providers for URL-certified standard transport calls.
 *
 * Called by: `providerRequestCall`. Endpoint names are not sources by
 * themselves; a call must use a generic transport and expose a matching literal
 * URL or object URL field.
 */
export function transportRequestCall(ts, call, ctx, facts, index, sourceRules) {
  const urls = endpointUrlTexts(ts, call, ctx, facts, index);
  if (!urls.length) return new Set();
  const out = new Set();
  for (const boundary of endpointBoundaries(sourceRules, { artifact: false })) {
    if (!transportMatchesBoundary(ts, call, ctx, index, boundary)) continue;
    if (!urls.some((url) => endpointMatches(boundary, url))) continue;
    out.add(boundary.module || boundary.symbol || boundary.boundary_id);
  }
  return out;
}

/** Match a resolved full name against module-call source rules.
 *
 * Called by: provider request and callable-alias detection.
 */
export function certifiedProviderModuleCall(fullName, sourceRules) {
  const match = providerModuleAndSuffix(fullName, sourceRules);
  if (!match) return null;
  for (const boundary of moduleBoundaries(sourceRules)) {
    if (boundary.module !== match.provider_module) continue;
    if (boundary.symbol.startsWith(".")) continue;
    if (normalizeProviderSuffix(boundary.symbol) === match.suffix) {
      return {
        kind: "provider_request",
        provider_module: match.provider_module,
        suffix: match.suffix,
        full_name: fullName,
      };
    }
  }
  return null;
}

/** Match a resolved full name against provider client constructor rules.
 *
 * Called by: `providerValueKind`.
 */
export function certifiedProviderClientConstructor(fullName) {
  if (!fullName) return null;
  for (const rule of TYPESCRIPT_PROVIDER_CLIENT_CONSTRUCTORS) {
    for (const moduleName of sorted(rule.modules)) {
      const prefix = `${moduleName}.`;
      if (fullName !== moduleName && !fullName.startsWith(prefix)) continue;
      const suffix = fullName === moduleName ? "" : fullName.slice(prefix.length);
      if (rule.suffixes.includes(suffix)) {
        return {
          kind: "provider_client_constructor",
          provider_module: moduleName,
          suffix,
          full_name: fullName,
        };
      }
    }
  }
  return null;
}

/** Return whether a suffix is a known provider client request method.
 *
 * Called by: provider-backed receiver and constructor-chain checks.
 */
export function isProviderClientRequestSuffix(suffix, sourceRules) {
  if (!suffix) return false;
  return moduleBoundaries(sourceRules).some((boundary) => normalizeProviderSuffix(boundary.symbol) === suffix);
}

/** Split a full name into provider module and suffix.
 *
 * Called by: `certifiedProviderModuleCall`. Longest module wins so scoped
 * packages are not shadowed by shorter prefixes.
 */
function providerModuleAndSuffix(fullName, sourceRules) {
  if (!fullName) return null;
  const modules = [...new Set(moduleBoundaries(sourceRules).map((boundary) => boundary.module))].sort(
    (left, right) => right.length - left.length || left.localeCompare(right),
  );
  for (const moduleName of modules) {
    if (fullName === moduleName) return { provider_module: moduleName, suffix: "" };
    const prefix = `${moduleName}.`;
    if (fullName.startsWith(prefix)) return { provider_module: moduleName, suffix: fullName.slice(prefix.length) };
  }
  return null;
}

/** Return source rules that describe provider SDK/module calls.
 *
 * Called by: provider certification helpers.
 */
function moduleBoundaries(sourceRules) {
  return (sourceRules || []).filter((boundary) => boundary.module && boundary.symbol);
}

/** Return source rules that describe URL endpoint transports.
 *
 * Called by: `transportRequestCall`.
 */
function endpointBoundaries(sourceRules, { artifact = null } = {}) {
  return (sourceRules || []).filter((boundary) => {
    if (!boundary.endpoint_patterns?.length) return false;
    if (artifact === null) return true;
    return Boolean(boundary.artifact_endpoint) === artifact;
  });
}

/** Normalize provider suffix spelling from source rules.
 *
 * Called by: source-rule matchers. A leading dot means "method on provider
 * value"; the suffix itself remains exact.
 */
function normalizeProviderSuffix(symbol) {
  return symbol.replace(/^\./, "");
}

/** Split a member expression into base expression plus dotted suffix.
 *
 * Called by: constructor-chain source matching.
 */
function splitMemberBaseAndSuffix(ts, expr) {
  const suffix = [];
  let current = unwrapExpression(ts, expr);
  while (current && (ts.isPropertyAccessExpression(current) || ts.isElementAccessExpression(current))) {
    if (ts.isPropertyAccessExpression(current)) suffix.unshift(current.name.text);
    else {
      const key = staticPropertyKeyText(ts, current.argumentExpression);
      if (!key) return null;
      suffix.unshift(key);
    }
    current = unwrapExpression(ts, current.expression);
  }
  return suffix.length ? { base: current, suffix } : null;
}

/** Return literal endpoint URL candidates from call arguments.
 *
 * Called by: URL-certified transport matching.
 */
function endpointUrlTexts(ts, call, ctx, facts, index) {
  return [...new Set(endpointUrlCandidates(ts, call, ctx, facts, index).map((candidate) => candidate.text))];
}

/** Return URL candidates with their exact URL expression.
 *
 * Called by: regular endpoint matching and artifact matching. Artifact sources
 * need the expression node so the analyzer can require tainted provider-derived
 * locator evidence on that URL, not merely elsewhere in the request object.
 */
function endpointUrlCandidates(ts, call, ctx, facts, index, urlInfoForExpression = null) {
  const out = [];
  for (const arg of call.arguments || []) {
    out.push(...endpointCandidatesForExpression(ts, arg, ctx, facts, index, urlInfoForExpression));
    if (ts.isObjectLiteralExpression?.(unwrapExpression(ts, arg))) {
      out.push(...objectEndpointUrlCandidates(ts, unwrapExpression(ts, arg), ctx, facts, index, urlInfoForExpression));
    }
  }
  return dedupeEndpointCandidates(out);
}

/** Return URL-like literal fields from an object literal argument.
 *
 * Called by: `endpointUrlTexts` for `request({ url })` and axios-style config.
 */
function objectEndpointUrlCandidates(ts, objectLiteral, ctx, facts, index, urlInfoForExpression) {
  const out = [];
  for (const property of objectLiteral.properties || []) {
    if (!ts.isPropertyAssignment?.(property)) continue;
    const key = objectPropertyName(ts, property.name);
    if (!["url", "uri", "baseURL", "baseUrl"].includes(key)) continue;
    out.push(...endpointCandidatesForExpression(ts, property.initializer, ctx, facts, index, urlInfoForExpression));
  }
  return out;
}

/** Return endpoint strings while preserving the expression that produced them. */
function endpointCandidatesForExpression(ts, expr, ctx, facts, index, urlInfoForExpression) {
  const texts = endpointTextsForExpression(ts, expr, ctx, facts, index);
  if (urlInfoForExpression) {
    for (const text of urlInfoForExpression(expr).strings) texts.push(text);
  }
  return texts.map((text) => ({ text, expression: expr }));
}

/** Return literal and propagated string URL candidates for an expression. */
function endpointTextsForExpression(ts, expr, ctx, facts, index) {
  const out = [];
  const literal = endpointStaticText(ts, expr);
  if (literal) out.push(literal);
  out.push(...endpointDerivedTexts(ts, expr));
  for (const ref of refsForReadExpr(ts, expr, ctx, facts, index, { includePrefixes: true })) {
    for (const text of facts.stringOf(ref)) out.push(text);
  }
  return out;
}

/** Deduplicate URL candidates without losing their provenance expression. */
function dedupeEndpointCandidates(candidates) {
  const out = [];
  const seen = new Set();
  for (const candidate of candidates) {
    const key = `${candidate.text}:${candidate.expression?.pos ?? ""}:${candidate.expression?.end ?? ""}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(candidate);
  }
  return out;
}

/** Return static text usable for endpoint matching.
 *
 * Called by: URL transport certification. Dynamic template holes are dropped
 * but static fragments are kept, so endpoint rules can still match stable
 * provider path pieces such as `/v1/responses` or `:generateContent`.
 */
function endpointStaticText(ts, expr) {
  const node = unwrapExpression(ts, expr);
  if (!node) return "";
  if (ts.isStringLiteralLike?.(node) || ts.isNoSubstitutionTemplateLiteral?.(node)) return node.text;
  if (ts.isTemplateExpression?.(node)) {
    return [node.head.text, ...node.templateSpans.map((span) => span.literal.text)].join("");
  }
  return "";
}

/** Return endpoint fragments embedded in URL-builder expressions.
 *
 * Called by: URL transport certification. This handles static may-analysis
 * cases where the transport receives a URL object/helper result instead of a
 * raw string, for example `fetch(new URL("api/chat", base))` or
 * `fetch(endpoint("chat/completions"))`.
 */
function endpointDerivedTexts(ts, expr) {
  const node = unwrapExpression(ts, expr);
  if (!node) return [];
  if (ts.isNewExpression(node) && exprPath(ts, node.expression) === "URL") {
    return endpointFragmentsFromArgs(ts, node.arguments || []);
  }
  if (ts.isCallExpression(node)) {
    return endpointFragmentsFromArgs(ts, node.arguments || []);
  }
  return [];
}

/** Return normalized literal endpoint fragments from call arguments. */
function endpointFragmentsFromArgs(ts, args) {
  const out = [];
  for (const arg of args || []) {
    const text = endpointStaticText(ts, arg);
    if (!text) continue;
    out.push(text);
    if (!/^(?:https?:|wss?:|\/)/i.test(text)) out.push(`/${text}`);
  }
  return out;
}

/** Return a literal property key for member-chain matching.
 *
 * Called by: constructor-chain provider matching. Unlike endpoint text, member
 * keys must be exact; computed templates with substitutions are not guessed.
 */
function staticPropertyKeyText(ts, expr) {
  const node = unwrapExpression(ts, expr);
  if (!node) return "";
  if (ts.isStringLiteralLike?.(node) || ts.isNumericLiteral(node)) return node.text;
  if (ts.isNoSubstitutionTemplateLiteral?.(node)) return node.text;
  return "";
}

/** Return a static object property name.
 *
 * Called by: object URL extraction.
 */
function objectPropertyName(ts, name) {
  if (ts.isIdentifier(name) || ts.isPrivateIdentifier?.(name)) return name.text;
  if (ts.isStringLiteralLike?.(name) || ts.isNumericLiteral(name)) return name.text;
  return "";
}

/** Return whether a call expression uses one boundary transport.
 *
 * Called by: URL-certified transport matching.
 */
function transportMatchesBoundary(ts, call, ctx, index, boundary) {
  return (boundary.endpoint_transports || []).some((transport) =>
    transportMatchesCall(ts, call, ctx, index, transport),
  );
}

/** Return whether a call expression uses one generic transport.
 *
 * Called by: `transportMatchesBoundary`. The match is intentionally limited to
 * standard transport names from source rules, not project wrapper names.
 */
function transportMatchesCall(ts, call, ctx, index, transport) {
  const expectedKind = ts.isNewExpression(call) ? "new" : "call";
  if ((transport.call_kind || "call") !== expectedKind) return false;
  const path = exprPath(ts, call.expression);
  if (transportNameMatchesPath(transport.callee, path)) return true;
  for (const fullName of fullNamesForExpression(ts, call.expression, ctx, index)) {
    if (transportNameMatchesPath(transport.callee, fullName)) return true;
  }
  return false;
}

/** Match a standard transport name against a local or resolved callee path.
 *
 * Called by: `transportMatchesCall`.
 */
function transportNameMatchesPath(name, path) {
  if (!path) return false;
  return path === name || path.startsWith(`${name}.`) || path.endsWith(`.${name}`);
}

/** Return whether a boundary endpoint regex matches a literal URL.
 *
 * Called by: URL-certified transport matching.
 */
function endpointMatches(boundary, url) {
  return (boundary.endpoint_patterns || []).some((pattern) => new RegExp(pattern, "i").test(url));
}

/** Return a sorted array from an iterable.
 *
 * Called by: constructor certification.
 */
function sorted(values) {
  return [...(values || [])].sort();
}
