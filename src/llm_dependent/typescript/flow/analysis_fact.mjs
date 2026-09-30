import {
  callFact,
  classFieldRef,
  CONTAINER_MUTATION_METHODS,
  controlCallFact,
  EVENT_PUBLISH_METHODS,
  EVENT_SUBSCRIPTION_METHODS,
  localRef,
  moduleRef,
  normalizeControlDependenceMode,
  paramDep,
  RECEIVER_CALLBACK_METHODS,
  RECEIVER_RETURN_METHODS,
  refKey,
  returnRef,
  spanKey,
  STATIC_CALLBACK_METHODS,
} from "./models.mjs";
import { FactStore } from "./facts.mjs";
import { buildProjectIndex } from "./indexing.mjs";
import { buildFactPayload } from "./payload.mjs";
import {
  functionContext,
  refsForPath,
  refsForReadExpr,
  resolveCall,
  resolveConstructor,
  resolveExprName,
  resolveInterfacePath,
  resolveName,
  targetRefs,
} from "./resolver.mjs";
import { uniqueBy } from "./resolver/utils.mjs";
import {
  providerArtifactDownloadCall,
  providerRequestCall,
  providerValueKind,
} from "./providers.mjs";
import { isTypescriptEndpointLikeString } from "../source_rules.mjs";
import {
  assignmentOperatorKinds,
  collectAssignedNames,
  collectDeclaredNames,
} from "./indexing/assignments.mjs";
import {
  exprPath,
  functionParams,
  isFunctionLikeWithBody,
} from "./syntax.mjs";
import { buildControlRegions } from "./fact_analysis/control_regions.mjs";
import {
  exprInfo,
  isDirectSourceOnly,
  mergeFieldInfo,
  mergeExprInfo,
  mergeInto,
} from "./fact_analysis/expr_info.mjs";
import {
  classMemberName,
  analysisSpanOf,
  expressionChildren,
  isNestedUnit,
  isSimpleReadExpression,
  unwrapTsExpression,
} from "./fact_analysis/syntax_helpers.mjs";
import {
  DirtyFunctionQueue,
  enqueueChangedRefs,
  recordCallEdge,
} from "./fact_analysis/worklist.mjs";

const DEFAULT_MAX_ITERATIONS = 80;
const DYNAMIC_OBJECT_FIELD = "<computed>";
const DEEP_OBJECT_FIELD = "<deep>";
const CHANNEL_PAYLOAD_FIELD = "<channel_payload>";
const MAX_GENERATED_REF_PATH_SEGMENTS = 12;

const SOURCE_TOKEN_STOP_WORDS = new Set([
  "https",
  "http",
  "wss",
  "api",
  "com",
  "v1",
  "v2",
  "call",
  "create",
  "stream",
  "fetch",
  "request",
]);

const TYPE_NAME_STOP_WORDS = new Set([
  "Array",
  "Awaited",
  "Boolean",
  "Date",
  "Error",
  "Map",
  "Number",
  "Object",
  "Promise",
  "Readonly",
  "Record",
  "Set",
  "String",
  "boolean",
  "false",
  "never",
  "null",
  "number",
  "object",
  "string",
  "true",
  "undefined",
  "unknown",
  "void",
]);
export function analyzeFactProject({
  ts,
  root,
  files,
  sourceRules,
  project = "typescript",
  options = {},
}) {
  const analyzer = new FlowAnalyzer({
    ts,
    root,
    files,
    sourceRules,
    project,
    options,
  });
  return analyzer.analyzeProject();
}
export class FlowAnalyzer {
  constructor({ ts, root, files, sourceRules, project, options }) {
    this.ts = ts;
    this.root = root;
    this.files = files;
    this.sourceRules = sourceRules || [];
    this.project = project;
    this.options = {
      controlDependenceMode: normalizeControlDependenceMode(options.controlDependenceMode),
      maxIterations: options.maxIterations || DEFAULT_MAX_ITERATIONS,
    };
    this.index = buildProjectIndex({ ts, root, files });
    this.functionOrder = orderedFunctions(this.index);
    this.classOrder = orderedClasses(this.index);
    this.functionsByKey = new Map(this.functionOrder.map((info) => [info.key, info]));
    this.annotationTypeCache = new Map();
    this.callersByCallee = new Map();
    this.localRefReaders = new Map();
    this.classFieldReaders = new Map();
    this.moduleRefReaders = new Map();
    this.descendantRefReaders = new Map();
    this.syntheticFunctionOwners = new Map();
    this.inlineFunctionValueScanDepth = 0;
    this.inlineSourceTokenSpecs = buildInlineSourceTokenSpecs(this.sourceRules);
    this.inlineSourceTextMisses = new WeakSet();
    this.inlineSourceHits = new WeakSet();
    this.facts = new FactStore();
  }
  analyzeProject() {
    const stats = this.runFixedPoint();
    const controlRegions = buildControlRegions({
      facts: this.facts,
      index: this.index,
      mode: this.options.controlDependenceMode,
    });
    return buildFactPayload({
      project: this.project,
      facts: this.facts,
      controlRegions,
      stats,
      options: this.options,
    });
  }
  runFixedPoint() {
    let iterations = 0;
    let converged = false;
    let currentBatch = this.functionOrder.map((info) => info.key);
    const queue = new DirtyFunctionQueue(this.functionOrder);

    for (let iteration = 1; iteration <= this.options.maxIterations; iteration += 1) {
      iterations = iteration;
      this.seedModuleBodyFacts();
      this.enqueueChangedRefs(queue);
      this.seedClassBodyFacts();
      this.enqueueChangedRefs(queue);
      currentBatch = mergeFunctionBatches(currentBatch, queue.drain());
      if (currentBatch.length === 0) {
        converged = true;
        break;
      }
      for (const functionId of currentBatch) {
        const info = this.functionsByKey.get(functionId);
        if (!info) continue;
        this.analyzeFunction(info);
        this.enqueueChangedRefs(queue, { ignoreLocalFunction: functionId });
      }
      currentBatch = queue.drain();
      if (currentBatch.length === 0) {
        converged = true;
        break;
      }
    }
    return {
      converged,
      iterations,
      maxIterations: this.options.maxIterations,
    };
  }
  seedModuleBodyFacts() {
    const files = [...this.index.files.values()].sort((left, right) => left.rel.localeCompare(right.rel));
    for (const file of files) {
      const ctx = this.makeModuleContext(file);
      for (const stmt of file.sourceFile.statements || []) this.seedModuleStatement(stmt, ctx);
    }
  }
  makeModuleContext(file) {
    const scope = this.index.moduleScopes.get(file.rel);
    return this.makeContext({
      key: `${file.rel}::<module>`,
      file: file.rel,
      node: file.sourceFile,
      sourceFile: file.sourceFile,
      text: file.text,
      name: "<module>",
      registerPath: "",
      kind: "module",
      qualname: "<module>",
      scope,
      parentScope: scope,
      classKey: "",
      enclosingClassKey: "",
      enclosingFunction: "",
      enclosingFunctions: [],
      start: 1,
      end: file.lines.length,
      span: { start: 1, end: file.lines.length },
      params: [],
      returnAnnotation: "",
      assignedNames: [],
      declaredNames: [],
    });
  }
  seedModuleStatement(stmt, ctx) {
    const span = this.markSpan(ctx.info, stmt);
    if (this.ts.isVariableStatement(stmt)) {
      for (const declaration of stmt.declarationList.declarations || []) {
        this.seedModuleTarget(declaration.name, declaration.initializer, ctx, span);
      }
      return;
    }
    if (this.ts.isExpressionStatement(stmt)) {
      const expr = unwrapTsExpression(this.ts, stmt.expression);
      if (this.ts.isBinaryExpression(expr) && assignmentOperatorKinds(this.ts).has(expr.operatorToken.kind)) {
        this.seedModuleTarget(expr.left, expr.right, ctx, span);
      }
      return;
    }
    if (this.ts.isExportAssignment?.(stmt) && stmt.expression) {
      const info = this.bindingValueInfo(stmt.expression, ctx, span);
      this.addInfoToRef(moduleRef(ctx.info.file, "default"), info, span, { taint: true });
    }
  }
  seedModuleTarget(target, valueExpr, ctx, span) {
    const valueInfo = this.bindingValueInfo(valueExpr, ctx, span);
    const refs = moduleTargetRefs(this.ts, target, ctx.info.file);
    for (const ref of refs) this.addInfoToRef(ref, valueInfo, span, { taint: true });
    this.propagateModulePatternFromPath(target, exprPath(this.ts, valueExpr), ctx, span);
    this.propagateModuleStructuredLiteralFields(valueExpr, refs, ctx, span);
  }
  propagateModulePatternFromPath(patternExpr, sourcePath, ctx, span) {
    if (!sourcePath) return;
    const pattern = unwrapTsExpression(this.ts, patternExpr);
    if (!pattern) return;
    if (this.ts.isObjectBindingPattern?.(pattern)) {
      for (const element of pattern.elements || []) {
        if (!this.ts.isBindingElement?.(element)) continue;
        const field = bindingElementFieldName(this.ts, element);
        const sourceInfo = element.dotDotDotToken || !field
          ? this.infoForPath(sourcePath, ctx)
          : this.infoForPath(`${sourcePath}.${field}`, ctx);
        for (const ref of moduleTargetRefs(this.ts, element.name, ctx.info.file)) {
          this.addInfoToRef(ref, sourceInfo, span, { taint: true });
        }
      }
    } else if (this.ts.isArrayBindingPattern?.(pattern)) {
      for (let index = 0; index < (pattern.elements || []).length; index += 1) {
        const element = pattern.elements[index];
        if (!element || this.ts.isOmittedExpression?.(element)) continue;
        const target = this.ts.isBindingElement?.(element) ? element.name : element;
        const sourceInfo = this.infoForPath(`${sourcePath}.${index}`, ctx);
        for (const ref of moduleTargetRefs(this.ts, target, ctx.info.file)) {
          this.addInfoToRef(ref, sourceInfo, span, { taint: true });
        }
      }
    }
  }
  propagateModuleStructuredLiteralFields(valueExpr, baseRefs, ctx, span) {
    const value = unwrapTsExpression(this.ts, valueExpr);
    if (!value || !this.ts.isObjectLiteralExpression?.(value) || !baseRefs.length) return;
    this.propagateObjectLiteralFields(value, baseRefs, ctx, span);
  }
  seedClassBodyFacts() {
    for (const classInfo of this.classOrder) {
      for (const member of classInfo.node.members || []) {
        if (this.ts.isPropertyDeclaration?.(member)) {
          this.seedClassPropertyFacts(classInfo, member);
        } else if (this.ts.isConstructorDeclaration?.(member)) {
          this.seedConstructorParameterPropertyFacts(classInfo, member);
        } else if (this.ts.isGetAccessorDeclaration?.(member)) {
          this.seedGetterPropertyFacts(classInfo, member);
        }
      }
    }
  }
  seedClassPropertyFacts(classInfo, member) {
    const fieldName = classMemberName(this.ts, member.name);
    if (!fieldName) return;
    const span = this.markSpan(classInfo, member);
    const valueInfo = this.classMemberValueInfo(classInfo, member.initializer, span);
    this.addAnnotatedTypeFacts(valueInfo, member.type, classInfo.scope, { includeClasses: true });
    this.addInfoToRef(classFieldRef(classInfo.key, fieldName), valueInfo, span, { taint: false });
  }
  seedConstructorParameterPropertyFacts(classInfo, constructorNode) {
    for (const param of constructorNode.parameters || []) {
      if (!isParameterProperty(this.ts, param)) continue;
      const fieldName = classMemberName(this.ts, param.name);
      if (!fieldName) continue;
      const span = this.markSpan(classInfo, param);
      const valueInfo = exprInfo();
      this.addAnnotatedTypeFacts(valueInfo, param.type, classInfo.scope, { includeClasses: true });
      this.addInfoToRef(classFieldRef(classInfo.key, fieldName), valueInfo, span, { taint: false });
    }
  }
  seedGetterPropertyFacts(classInfo, getterNode) {
    const fieldName = classMemberName(this.ts, getterNode.name);
    const getterInfo = this.index.functionByNode.get(getterNode);
    if (!fieldName || !getterInfo) return;
    const span = this.markSpan(classInfo, getterNode);
    const valueInfo = exprInfo();
    this.addAnnotatedTypeFacts(valueInfo, getterNode.type, getterInfo.scope, { includeClasses: true });
    this.mergeReturnFacts(valueInfo, getterInfo.key);
    this.addInfoToRef(classFieldRef(classInfo.key, fieldName), valueInfo, span, { taint: false });
  }
  classMemberValueInfo(classInfo, initializer, span) {
    const valueInfo = exprInfo();
    if (!initializer) return valueInfo;
    const ctx = functionContext({
      ...classInfo,
      key: `${classInfo.key}::<class_body>`,
      params: [],
      assignedNames: [],
      declaredNames: [],
      classKey: classInfo.key,
      enclosingClassKey: classInfo.key,
    });
    return this.bindingValueInfo(initializer, ctx, span);
  }
  addAnnotatedTypeFacts(info, typeNode, scope, options = {}) {
    if (!typeNode) return;
    mergeInto(info.types, this.typeIdsForAnnotation(typeNode.getText(), scope, options));
  }
  seedAnnotatedFieldTypeFacts(baseRef, annotation, scope, seen = new Set()) {
    for (const typeId of this.typeIdsForAnnotation(annotation, scope)) {
      if (seen.has(typeId)) continue;
      seen.add(typeId);
      const interfaceInfo = this.index.interfaces.get(typeId);
      if (!interfaceInfo) continue;
      for (const member of interfaceInfo.node.members || []) {
        const field = classMemberName(this.ts, member.name);
        if (!field || !member.type) continue;
        const fieldRef = appendRefPath(baseRef, field);
        const fieldAnnotation = member.type.getText(interfaceInfo.sourceFile);
        this.facts.addType(fieldRef, this.typeIdsForAnnotation(fieldAnnotation, interfaceInfo.scope));
        this.seedAnnotatedFieldTypeFacts(fieldRef, fieldAnnotation, interfaceInfo.scope, seen);
      }
    }
  }
  analyzeFunction(info) {
    const ctx = this.makeContext(info);
    this.seedFunctionParamDeps(info);
    if (this.ts.isBlock(info.node.body)) {
      this.analyzeBlock(info.node.body.statements, ctx);
      return;
    }
    const span = this.markSpan(info, info.node.body);
    const valueInfo = this.bindingValueInfo(info.node.body, ctx, span);
    this.propagateReturn(valueInfo, ctx, span);
  }
  seedFunctionParamDeps(info) {
    const defaultCtx = this.makeContext({
      ...info,
      key: `${info.key}::<parameter_defaults>`,
    });
    for (const param of info.params || []) {
      const ref = localRef(info.key, param.name);
      const defaultRef = localRef(defaultCtx.info.key, param.name);
      this.facts.addParamDep(ref, [paramDep(info.key, param.name)]);
      this.facts.addType(ref, this.typeIdsForAnnotation(param.annotation, info.scope));
      this.facts.addType(defaultRef, this.typeIdsForAnnotation(param.annotation, info.scope));
      this.seedAnnotatedFieldTypeFacts(ref, param.annotation, info.scope);
      this.seedAnnotatedFieldTypeFacts(defaultRef, param.annotation, info.scope);
      if (param.initializer) {
        const span = this.markSpan(info, param.initializer);
        const defaultInfo = this.bindingValueInfo(param.initializer, defaultCtx, span);
        this.addInfoToRef(defaultRef, defaultInfo, span, { taint: false });
        this.addFieldInfosToRef(defaultRef, defaultInfo, span, { taint: false });
        this.addInfoToRef(ref, defaultInfo, span, { taint: false });
        this.addFieldInfosToRef(ref, defaultInfo, span, { taint: false });
      }
    }
  }
  typeIdsForAnnotation(annotation, scope, options = {}) {
    const cacheKey = `${scope}:${options.includeClasses ? "classes" : "interfaces"}:${annotation || ""}`;
    if (this.annotationTypeCache.has(cacheKey)) return new Set(this.annotationTypeCache.get(cacheKey));
    const out = new Set();
    for (const name of typeNamesInAnnotation(annotation)) {
      mergeInto(out, resolveInterfacePath(this.index, scope, name));
      for (const resolved of resolveName(name, scope, this.index)) {
        if (options.includeClasses && resolved.class) out.add(resolved.class);
      }
    }
    this.annotationTypeCache.set(cacheKey, new Set(out));
    return out;
  }
  makeContext(info, controlOrigin = null) {
    return functionContext(info, controlOrigin);
  }
  analyzeBlock(statements, ctx) {
    for (const stmt of statements || []) this.analyzeStatement(stmt, ctx);
  }
  analyzeStatement(stmt, ctx) {
    if (isNestedUnit(this.ts, stmt)) return;
    const span = this.markSpan(ctx.info, stmt);
    if (ctx.control_origin) this.facts.addDataEdge(span, [ctx.control_origin], "control");

    if (this.ts.isVariableStatement(stmt)) this.handleVariableStatement(stmt, ctx, span);
    else if (this.ts.isExpressionStatement(stmt)) this.handleExpressionStatement(stmt, ctx, span);
    else if (this.ts.isReturnStatement(stmt)) this.handleReturnStatement(stmt, ctx, span);
    else if (this.ts.isIfStatement(stmt)) this.handleIfStatement(stmt, ctx, span);
    else if (this.ts.isWhileStatement(stmt) || this.ts.isDoStatement(stmt)) this.handleLoopStatement(stmt, ctx, span);
    else if (this.ts.isForStatement(stmt)) this.handleForStatement(stmt, ctx, span);
    else if (this.ts.isForOfStatement(stmt) || this.ts.isForInStatement(stmt)) this.handleForEachStatement(stmt, ctx, span);
    else if (this.ts.isSwitchStatement(stmt)) this.handleSwitchStatement(stmt, ctx, span);
    else if (this.ts.isTryStatement(stmt)) this.handleTryStatement(stmt, ctx, span);
    else this.handleFallbackStatement(stmt, ctx, span);
  }
  markSpan(info, node) {
    const span = analysisSpanOf(this.ts, info.sourceFile, node);
    return {
      filepath: info.file,
      start_line: span.start,
      end_line: span.end,
      kind: "statement",
      qualname: info.qualname || "",
    };
  }
  evalExpr(expr, ctx, span) {
    const node = unwrapTsExpression(this.ts, expr);
    if (!node) return exprInfo();
    if (this.ts.isCallExpression(node) || this.ts.isNewExpression(node)) return this.handleCall(node, ctx, span);
    if (isNestedUnit(this.ts, node)) return this.functionValueInfo(node, ctx, span);

    const info = this.readRefFacts(
      refsForReadExpr(this.ts, node, ctx, this.facts, this.index, { includePrefixes: true }), ctx.info.key,
    );
    mergeInto(info.strings, stringFragmentsForExpression(this.ts, node, this.sourceRules));
    for (const resolved of resolveExprName(this.ts, node, ctx.info.scope, this.index)) {
      if (resolved.function) info.aliases.add(resolved.function);
      if (resolved.class) info.types.add(resolved.class);
    }
    mergeInto(info.providers, providerValueKind(this.ts, node, ctx, this.facts, this.index));
    if (isSimpleReadExpression(this.ts, node)) return info;
    for (const child of expressionChildren(this.ts, node)) {
      this.mergeChildExprInfo(info, node, child, this.evalExpr(child, ctx, span));
    }
    return info;
  }
  bindingValueInfo(expr, ctx, span) {
    const info = this.evalExpr(expr, ctx, span);
    mergeExprInfo(info, this.externalCallResultInfo(expr, ctx, span));
    const value = unwrapTsExpression(this.ts, expr);
    if (value && this.ts.isObjectLiteralExpression?.(value)) {
      this.mergeObjectLiteralFieldInfos(info, value, ctx, span);
    }
    return info;
  }
  externalCallResultInfo(expr, ctx, span) {
    const node = unwrapTsExpression(this.ts, expr);
    if (!node || (!this.ts.isCallExpression(node) && !this.ts.isNewExpression(node))) return exprInfo();
    if (providerRequestCall(this.ts, node, ctx, this.facts, this.index, this.sourceRules).size) return exprInfo();
    const urlInfoForExpression = this.memoizedUrlInfoForExpression(ctx, span);
    if (providerArtifactDownloadCall(
      this.ts,
      node,
      ctx,
      this.facts,
      this.index,
      this.sourceRules,
      urlInfoForExpression,
    ).size) {
      return exprInfo();
    }
    if (resolveCall(this.ts, node, ctx, this.facts, this.index).length) return exprInfo();
    const result = exprInfo();
    const receiverInfo = this.callReceiverInfo(node, ctx, span);
    const args = [...(node.arguments || [])];
    const argInfos = args.map((arg) => this.evalExpr(arg, ctx, span));
    mergeTaintFacts(result, receiverInfo);
    for (const argInfo of argInfos) mergeTaintFacts(result, argInfo);
    if (this.externalCallMayReturnEndpointString(node)) {
      mergeInto(result.strings, receiverInfo.strings);
      for (const argInfo of argInfos) mergeInto(result.strings, argInfo.strings);
    }
    return result;
  }
  externalCallMayReturnEndpointString(call) {
    const callee = unwrapTsExpression(this.ts, call.expression);
    const path = exprPath(this.ts, callee);
    if (this.ts.isNewExpression(call) && transportNameMatchesSuffix(path, "URL")) return true;
    if (path === "String" || path.endsWith(".String")) return true;
    return this.ts.isPropertyAccessExpression(callee) && callee.name.text === "toString";
  }
  mergeChildExprInfo(target, parent, child, childInfo) {
    if (this.childValueMayBecomeParentValue(parent, child)) {
      mergeExprInfo(target, childInfo);
      return;
    }
    mergeTaintFacts(target, childInfo);
    if (this.parentMayContainChildEndpointString(parent)) mergeInto(target.strings, childInfo.strings);
  }
  parentMayContainChildEndpointString(parent) {
    if (this.ts.isTemplateExpression?.(parent) || this.ts.isTaggedTemplateExpression?.(parent)) return true;
    return this.ts.isBinaryExpression(parent) && parent.operatorToken.kind === this.ts.SyntaxKind.PlusToken;
  }
  childValueMayBecomeParentValue(parent, child) {
    if (this.ts.isAwaitExpression?.(parent)) return child === parent.expression;
    if (this.ts.isConditionalExpression(parent)) {
      return child === parent.whenTrue || child === parent.whenFalse;
    }
    if (this.ts.isBinaryExpression(parent)) {
      return (
        child === parent.left ||
        child === parent.right
      ) && valueSelectingBinaryOperators(this.ts).has(parent.operatorToken.kind);
    }
    return false;
  }
  functionValueInfo(node, ctx = null, span = null) {
    const info = exprInfo();
    const functionInfo = this.index.functionByNode?.get(node);
    const classInfo = this.index.classByNode?.get(node);
    if (functionInfo) info.aliases.add(functionInfo.key);
    else if (
      ctx &&
      span &&
      isFunctionLikeWithBody(this.ts, node) &&
      (this.inlineFunctionValueScanDepth > 0 || this.inlineCallbackMayContainSource(node, ctx, span))
    ) {
      const { info: inlineInfo } = this.analyzeSourceBearingInlineCallback(node, ctx, span);
      info.aliases.add(inlineInfo.key);
    }
    if (classInfo) info.types.add(classInfo.key);
    return info;
  }
  handleVariableStatement(stmt, ctx, span) {
    for (const declaration of stmt.declarationList.declarations || []) {
      const valueInfo = this.bindingValueInfo(declaration.initializer, ctx, span);
      this.propagateAssignment(valueInfo, [declaration.name], ctx, span);
      this.copyDescendantFactsFromExpression(declaration.initializer, [declaration.name], ctx, span);
      this.propagateDestructuringFromInitializer(declaration.initializer, declaration.name, ctx, span);
      this.propagateStructuredLiteralFields(declaration.initializer, [declaration.name], ctx, span);
    }
  }
  handleExpressionStatement(stmt, ctx, span) {
    const expr = unwrapTsExpression(this.ts, stmt.expression);
    if (this.ts.isBinaryExpression(expr) && assignmentOperatorKinds(this.ts).has(expr.operatorToken.kind)) {
      const leftInfo = expr.operatorToken.kind === this.ts.SyntaxKind.EqualsToken ? exprInfo() : this.evalExpr(expr.left, ctx, span);
      const rightInfo = this.bindingValueInfo(expr.right, ctx, span);
      const valueInfo = mergeExprInfo(leftInfo, rightInfo);
      this.propagateAssignment(valueInfo, [expr.left], ctx, span);
      this.copyDescendantFactsFromExpression(expr.right, [expr.left], ctx, span);
      this.propagateDestructuringFromInitializer(expr.right, expr.left, ctx, span);
      this.propagateStructuredLiteralFields(expr.right, [expr.left], ctx, span);
      return;
    }
    const info = this.evalExpr(expr, ctx, span);
    if (info.origins.size && !isDirectSourceOnly(info)) this.facts.addDataEdge(span, edgeOrigins(info), "access");
  }
  handleReturnStatement(stmt, ctx, span) {
    const valueInfo = this.bindingValueInfo(stmt.expression, ctx, span);
    this.propagateReturn(valueInfo, ctx, span);
  }
  propagateAssignment(valueInfo, targets, ctx, span) {
    const refs = targets.flatMap((target) => targetRefs(this.ts, target, ctx, this.facts, this.index));
    for (const ref of refs) {
      this.addInfoToRef(ref, valueInfo, span, { taint: true });
      this.addFieldInfosToRef(ref, valueInfo, span, { taint: true });
    }
    if (valueInfo.origins.size && !isDirectSourceOnly(valueInfo)) {
      this.facts.addDataEdge(span, edgeOrigins(valueInfo), "assignment");
    }
    const fieldOrigins = new Set();
    for (const fieldInfo of valueInfo.fieldInfos.values()) {
      if (!isDirectSourceOnly(fieldInfo)) mergeInto(fieldOrigins, edgeOrigins(fieldInfo));
    }
    if (fieldOrigins.size) this.facts.addBridgeEdge(span, fieldOrigins, "assignment");
  }
  propagateReturn(valueInfo, ctx, span) {
    const ref = returnRef(ctx.info.key);
    this.facts.addProvider(ref, valueInfo.providers);
    this.facts.addType(ref, valueInfo.types);
    this.facts.addAlias(ref, valueInfo.aliases);
    this.facts.addString(ref, valueInfo.strings);
    this.addReturnFieldInfosToRef(ref, valueInfo, ctx, span);
    if (valueInfo.origins.size) {
      const currentDeps = this.currentParamDeps(valueInfo, ctx.info.key);
      const paramOnly = this.isParamOnlyValue(valueInfo, currentDeps);
      if (paramOnly) this.facts.addReturnParamDeps(ctx.info.key, currentDeps, span);
      else this.facts.addReturn(ctx.info.key, [span]);
      if (!isDirectSourceOnly(valueInfo)) this.facts.addDataEdge(span, edgeOrigins(valueInfo), "return");
    }
  }
  addInfoToRef(ref, info, span, { taint }) {
    this.facts.addProvider(ref, info.providers);
    this.facts.addType(ref, info.types);
    this.facts.addAlias(ref, info.aliases);
    this.facts.addParamDep(ref, info.paramDeps);
    this.facts.addString(ref, info.strings);
    if (taint && info.origins.size) {
      this.facts.addTaint(ref, [span]);
      if (this.isParamOnlyValue(info, info.paramDeps)) this.facts.addParamTaint(ref, [span]);
    }
  }
  addFieldInfosToRef(ref, info, span, { taint }) {
    for (const [suffix, fieldInfo] of info.fieldInfos || []) {
      if (!infoHasCapabilityFacts(fieldInfo)) continue;
      this.addInfoToRef(appendRefPath(ref, suffix), fieldInfo, span, { taint });
    }
  }
  addReturnFieldInfosToRef(ref, info, ctx, span) {
    for (const [suffix, fieldInfo] of info.fieldInfos || []) {
      if (!infoHasCapabilityFacts(fieldInfo)) continue;
      const currentDeps = this.currentParamDeps(fieldInfo, ctx.info.key);
      const taint = !this.isParamOnlyValue(fieldInfo, currentDeps);
      this.addInfoToRef(appendRefPath(ref, suffix), fieldInfo, span, { taint });
    }
  }
  infoForPath(pathValue, ctx) {
    return this.readRefFacts(
      refsForPath(pathValue, ctx, this.facts, this.index, { includePrefixes: true }), ctx.info.key,
    );
  }
  propagateDestructuringFromInitializer(valueExpr, targetPattern, ctx, span) {
    const sourcePath = exprPath(this.ts, valueExpr);
    if (!sourcePath) return;
    this.propagatePatternFromPath(targetPattern, sourcePath, ctx, span);
  }
  propagatePatternFromPath(patternExpr, sourcePath, ctx, span) {
    const pattern = unwrapTsExpression(this.ts, patternExpr);
    if (!pattern) return;
    if (this.ts.isObjectBindingPattern?.(pattern)) {
      this.propagateObjectBindingFromPath(pattern, sourcePath, ctx, span);
    } else if (this.ts.isArrayBindingPattern?.(pattern)) {
      this.propagateArrayBindingFromPath(pattern, sourcePath, ctx, span);
    } else if (this.ts.isObjectLiteralExpression?.(pattern)) {
      this.propagateObjectAssignmentPatternFromPath(pattern, sourcePath, ctx, span);
    } else if (this.ts.isArrayLiteralExpression?.(pattern)) {
      this.propagateArrayAssignmentPatternFromPath(pattern, sourcePath, ctx, span);
    }
  }
  propagateObjectBindingFromPath(pattern, sourcePath, ctx, span) {
    for (const element of pattern.elements || []) {
      if (!this.ts.isBindingElement?.(element)) continue;
      if (element.dotDotDotToken) {
        this.propagateAssignment(this.infoForPath(sourcePath, ctx), [element.name], ctx, span);
        continue;
      }
      const field = bindingElementFieldName(this.ts, element);
      if (!field) continue;
      this.propagateDestructuredField(`${sourcePath}.${field}`, element.name, element.initializer, ctx, span);
    }
  }
  propagateArrayBindingFromPath(pattern, sourcePath, ctx, span) {
    for (let index = 0; index < (pattern.elements || []).length; index += 1) {
      const element = pattern.elements[index];
      if (!element || this.ts.isOmittedExpression?.(element)) continue;
      if (this.ts.isBindingElement?.(element) && element.dotDotDotToken) {
        this.propagateAssignment(this.infoForPath(sourcePath, ctx), [element.name], ctx, span);
        continue;
      }
      const target = this.ts.isBindingElement?.(element) ? element.name : element;
      const fallback = this.ts.isBindingElement?.(element) ? element.initializer : null;
      this.propagateDestructuredField(`${sourcePath}.${index}`, target, fallback, ctx, span);
    }
  }
  propagateObjectAssignmentPatternFromPath(pattern, sourcePath, ctx, span) {
    for (const property of pattern.properties || []) {
      if (this.ts.isSpreadAssignment?.(property)) {
        this.propagateAssignment(this.infoForPath(sourcePath, ctx), [property.expression], ctx, span);
      } else if (this.ts.isShorthandPropertyAssignment?.(property)) {
        this.propagateDestructuredField(
          `${sourcePath}.${property.name.text}`,
          property.name,
          property.objectAssignmentInitializer,
          ctx,
          span,
        );
      } else if (this.ts.isPropertyAssignment?.(property)) {
        const field = classMemberName(this.ts, property.name);
        if (field) this.propagateDestructuredField(`${sourcePath}.${field}`, property.initializer, null, ctx, span);
      }
    }
  }
  propagateArrayAssignmentPatternFromPath(pattern, sourcePath, ctx, span) {
    for (let index = 0; index < (pattern.elements || []).length; index += 1) {
      const element = pattern.elements[index];
      if (!element || this.ts.isOmittedExpression?.(element)) continue;
      if (this.ts.isSpreadElement?.(element)) {
        this.propagateAssignment(this.infoForPath(sourcePath, ctx), [element.expression], ctx, span);
      } else {
        this.propagateDestructuredField(`${sourcePath}.${index}`, element, null, ctx, span);
      }
    }
  }
  propagateDestructuredField(sourcePath, target, fallbackExpr, ctx, span) {
    const fieldInfo = this.infoForPath(sourcePath, ctx);
    if (fallbackExpr) mergeExprInfo(fieldInfo, this.bindingValueInfo(fallbackExpr, ctx, span));
    this.propagateAssignment(fieldInfo, [target], ctx, span);
    this.copyDescendantFactsFromPath(sourcePath, [target], ctx, span);
    this.propagatePatternFromPath(target, sourcePath, ctx, span);
  }
  copyDescendantFactsFromPath(sourcePath, targets, ctx, span) {
    this.copyDescendantFactsFromRefs(
      refsForPath(sourcePath, ctx, this.facts, this.index, { includePrefixes: false }),
      targets,
      ctx,
      span,
    );
  }
  copyDescendantFactsFromExpression(sourceExpr, targets, ctx, span) {
    if (!sourceExpr) return;
    this.copyDescendantFactsFromRefs(
      refsForReadExpr(this.ts, sourceExpr, ctx, this.facts, this.index, { includePrefixes: false }),
      targets,
      ctx,
      span,
    );
  }
  copyDescendantFactsFromRefs(sourceBaseRefs, targets, ctx, span) {
    const targetBaseRefs = targets.flatMap((target) => targetRefs(this.ts, target, ctx, this.facts, this.index));
    if (!targetBaseRefs.length) return;
    for (const sourceBaseRef of sourceBaseRefs) {
      this.recordDescendantRefRead(sourceBaseRef, ctx.info.key);
      for (const { ref: sourceRef, suffix } of this.facts.descendantRefsOf(sourceBaseRef)) {
        const info = exprInfo();
        this.mergeRefFacts(info, sourceRef);
        if (!infoHasFacts(info)) continue;
        if (info.origins.size) this.facts.addBridgeEdge(span, edgeOrigins(info), "assignment");
        for (const targetBaseRef of targetBaseRefs) {
          this.addInfoToRef(appendRefPath(targetBaseRef, suffix), info, span, { taint: true });
        }
      }
    }
  }
  propagateStructuredLiteralFields(valueExpr, targets, ctx, span) {
    const value = unwrapTsExpression(this.ts, valueExpr);
    if (!value || !this.ts.isObjectLiteralExpression?.(value)) return;
    const baseRefs = targets.flatMap((target) => targetRefs(this.ts, target, ctx, this.facts, this.index));
    if (!baseRefs.length) return;
    this.propagateObjectLiteralFields(value, baseRefs, ctx, span);
  }
  mergeObjectLiteralFieldInfos(info, objectLiteral, ctx, span) {
    for (const property of objectLiteral.properties || []) {
      if (this.ts.isSpreadAssignment?.(property)) {
        mergeExprInfo(info, this.spreadDescendantFieldInfo(property.expression, ctx, span));
        continue;
      }
      const field = objectLiteralFieldName(this.ts, property);
      const initializer = objectLiteralPropertyValue(this.ts, property);
      if (!field || !initializer) continue;
      const fieldInfo = this.bindingValueInfo(initializer, ctx, span);
      if (infoHasCapabilityFacts(fieldInfo)) mergeFieldInfo(info, field, fieldInfo);
    }
  }
  spreadDescendantFieldInfo(spreadExpr, ctx, span) {
    const info = this.bindingValueInfo(spreadExpr, ctx, span);
    for (const sourceBaseRef of refsForReadExpr(this.ts, spreadExpr, ctx, this.facts, this.index, { includePrefixes: false })) {
      this.recordDescendantRefRead(sourceBaseRef, ctx.info.key);
      for (const { ref: sourceRef, suffix } of this.facts.descendantRefsOf(sourceBaseRef)) {
        const fieldInfo = exprInfo();
        this.mergeRefFacts(fieldInfo, sourceRef);
        if (infoHasCapabilityFacts(fieldInfo)) mergeFieldInfo(info, suffix, fieldInfo);
      }
    }
    return info;
  }
  propagateObjectLiteralFields(objectLiteral, baseRefs, ctx, span) {
    for (const property of objectLiteral.properties || []) {
      const field = objectLiteralFieldName(this.ts, property);
      if (!field) {
        if (this.ts.isSpreadAssignment?.(property)) {
          const spreadInfo = this.spreadDescendantFieldInfo(property.expression, ctx, span);
          for (const baseRef of baseRefs) {
            this.addInfoToRef(baseRef, spreadInfo, span, { taint: true });
            this.addFieldInfosToRef(baseRef, spreadInfo, span, { taint: true });
          }
        }
        continue;
      }
      const initializer = objectLiteralPropertyValue(this.ts, property);
      if (!initializer) continue;
      const fieldRefs = baseRefs.map((ref) => appendRefPath(ref, field));
      const valueInfo = this.bindingValueInfo(initializer, ctx, span);
      for (const fieldRef of fieldRefs) this.addInfoToRef(fieldRef, valueInfo, span, { taint: true });
      const nested = unwrapTsExpression(this.ts, initializer);
      if (nested && this.ts.isObjectLiteralExpression?.(nested)) {
        this.propagateObjectLiteralFields(nested, fieldRefs, ctx, span);
      }
    }
  }
  handleCall(call, ctx, span) {
    const result = exprInfo();
    const staticUrlArg = standardUrlConstructorArgument(this.ts, call);
    if (staticUrlArg) {
      mergeInto(result.strings, stringFragmentsForExpression(this.ts, staticUrlArg, this.sourceRules));
    }
    this.recordCallCalleeRead(call, ctx);
    const receiverInfo = this.callReceiverInfo(call, ctx, span);
    const calleeInfo = this.callCalleeInfo(call, ctx);
    const args = [...(call.arguments || [])];
    const argInfos = args.map((arg) => this.evalExpr(arg, ctx, span));

    const sourceProviders = providerRequestCall(this.ts, call, ctx, this.facts, this.index, this.sourceRules);
    const urlInfoForExpression = this.memoizedUrlInfoForExpression(ctx, span);
    for (const provider of providerArtifactDownloadCall(
      this.ts,
      call,
      ctx,
      this.facts,
      this.index,
      this.sourceRules,
      urlInfoForExpression,
    )) {
      sourceProviders.add(provider);
    }
    if (sourceProviders.size) {
      this.facts.addSource(span);
      result.origins.add(span);
      result.directSources.add(span);
      this.activateSourceCallbacks(call, ctx, span, result);
      return result;
    }

    const inputInfo = exprInfo();
    mergeTaintFacts(inputInfo, receiverInfo);
    for (const argInfo of argInfos) mergeTaintFacts(inputInfo, argInfo);
    const inputOrigins = edgeOrigins(inputInfo);
    this.handleContainerMutation(call, ctx, span, argInfos);
    this.handleEventPublishFlow(call, ctx, span, argInfos);
    this.applyCallbackFlow(call, ctx, span, receiverInfo, argInfos, result);
    this.applyEventSubscriptionFlow(call, ctx, span, receiverInfo, calleeInfo, result);
    this.scanSourceBearingInlineCallbacks(call, ctx, span);

    const targets = resolveCall(this.ts, call, ctx, this.facts, this.index);
    if (targets.length) {
      if (inputOrigins.size) {
        this.facts.addDataEdge(span, inputOrigins, "caller");
      } else if (ctx.control_origin) {
        for (const target of targets) {
          this.facts.addControlCall(controlCallFact(ctx.info.key, target.key, span, ctx.control_origin));
        }
      }
      for (const target of targets) {
        this.recordCall(callFact(ctx.info.key, target.key, span));
        const actualInfosByParam = this.seedCalleeArguments(target, receiverInfo, argInfos, call, ctx, span);
        this.mergeReturnFacts(result, target.key);
        this.mergeReturnFieldFacts(result, target.key);
        mergeExprInfo(result, this.instantiateReturnParamDeps(target.key, actualInfosByParam));
        this.instantiateReturnFieldParamDeps(result, target.key, actualInfosByParam);
      }
    } else {
      if (inputOrigins.size) this.facts.addDataEdge(span, inputOrigins, "access");
    }

    if (this.callReturnsReceiverTaint(call) && receiverInfo.origins.size) this.addDerivedTaint(result, span, receiverInfo);
    if (this.callReturnsPromiseCombinatorTaint(call) && inputOrigins.size) this.addDerivedTaint(result, span, inputInfo);
    mergeInto(result.providers, providerValueKind(this.ts, call, ctx, this.facts, this.index));
    mergeInto(result.types, resolveConstructor(this.ts, call, ctx, this.index));
    if (result.types.size && inputOrigins.size) this.addDerivedTaint(result, span, inputInfo);
    return result;
  }
  memoizedUrlInfoForExpression(ctx, span) {
    const memo = new Map();
    return (expr) => {
      const key = `${expr?.pos ?? ""}:${expr?.end ?? ""}`;
      if (!memo.has(key)) memo.set(key, this.bindingValueInfo(expr, ctx, span));
      return memo.get(key);
    };
  }
  handleContainerMutation(call, ctx, span, argInfos) {
    const callee = unwrapTsExpression(this.ts, call.expression);
    if (!this.ts.isPropertyAccessExpression(callee) && !this.ts.isElementAccessExpression(callee)) return;
    const method = this.callbackMethodName(callee);
    if (!CONTAINER_MUTATION_METHODS.has(method)) return;
    const storedInfo = exprInfo();
    for (const argInfo of storedContainerValueInfos(method, argInfos)) mergeExprInfo(storedInfo, argInfo);
    if (!infoHasFacts(storedInfo)) return;
    for (const ref of targetRefs(this.ts, callee.expression, ctx, this.facts, this.index)) {
      this.addInfoToRef(ref, storedInfo, span, { taint: true });
    }
    if (storedInfo.origins.size) this.facts.addDataEdge(span, edgeOrigins(storedInfo), "assignment");
  }
  recordCallCalleeRead(call, ctx) {
    const callee = unwrapTsExpression(this.ts, call.expression);
    for (const ref of refsForReadExpr(this.ts, callee, ctx, this.facts, this.index, { includePrefixes: true })) {
      this.recordRefRead(ref, ctx.info.key);
    }
  }
  applyCallbackFlow(call, ctx, span, receiverInfo, argInfos, result) {
    for (const route of this.callbackRoutes(call, receiverInfo, argInfos)) {
      const callback = (call.arguments || [])[route.callbackArgIndex];
      if (!callback || this.ts.isSpreadElement?.(callback)) continue;
      if (route.sourceInfo.origins.size) this.facts.addDataEdge(span, edgeOrigins(route.sourceInfo), "caller");
      this.activateCallback(callback, route.paramIndexes, route.sourceInfo, ctx, span, result);
    }
  }
  callbackRoutes(call, receiverInfo, argInfos) {
    const routes = [];
    const callee = unwrapTsExpression(this.ts, call.expression);

    if (this.ts.isPropertyAccessExpression(callee) || this.ts.isElementAccessExpression(callee)) {
      const method = this.callbackMethodName(callee);
      for (const spec of RECEIVER_CALLBACK_METHODS.get(method) || []) {
        if (!receiverInfo.origins.size) continue;
        routes.push({
          callbackArgIndex: spec.arg,
          paramIndexes: spec.params,
          sourceInfo: receiverInfo,
        });
      }
    }

    const staticSpec = STATIC_CALLBACK_METHODS.get(exprPath(this.ts, callee));
    const sourceInfo = staticSpec ? argInfos[staticSpec.sourceArgIndex] : null;
    if (sourceInfo?.origins.size) {
      for (const spec of staticSpec.callbacks) {
        routes.push({
          callbackArgIndex: spec.arg,
          paramIndexes: spec.params,
          sourceInfo,
        });
      }
    }
    return routes;
  }
  callbackMethodName(callee) {
    if (this.ts.isPropertyAccessExpression(callee)) return callee.name.text;
    if (this.ts.isElementAccessExpression(callee)) {
      const arg = callee.argumentExpression;
      if (arg && this.ts.isStringLiteralLike(arg)) return arg.text;
    }
    return "";
  }
  activateCallback(callbackExpr, paramIndexes, sourceInfo, ctx, span, result) {
    const callback = unwrapTsExpression(this.ts, callbackExpr);
    if (isFunctionLikeWithBody(this.ts, callback)) {
      const { info: callbackInfo, actualInfosByParam } = this.analyzeInlineCallback(callback, paramIndexes, sourceInfo, ctx, span);
      this.mergeReturnFacts(result, callbackInfo.key);
      mergeExprInfo(result, this.instantiateReturnParamDeps(callbackInfo.key, actualInfosByParam));
      return;
    }

    for (const target of this.resolveCallbackTargets(callback, ctx)) {
      this.recordCall(callFact(ctx.info.key, target.key, span));
      const actualInfosByParam = this.seedCallbackTargetArguments(target, paramIndexes, sourceInfo, span);
      this.mergeReturnFacts(result, target.key);
      mergeExprInfo(result, this.instantiateReturnParamDeps(target.key, actualInfosByParam));
    }
  }
  activateSourceCallbacks(call, ctx, span, sourceInfo) {
    for (const arg of call.arguments || []) {
      if (this.ts.isSpreadElement?.(arg)) {
        this.activateSourceCallbackExpression(arg.expression, ctx, span, sourceInfo);
      } else {
        this.activateSourceCallbackExpression(arg, ctx, span, sourceInfo);
      }
    }
  }
  activateSourceCallbackExpression(expr, ctx, span, sourceInfo) {
    const node = unwrapTsExpression(this.ts, expr);
    if (!node) return;
    if (isFunctionLikeWithBody(this.ts, node)) {
      this.activateCallback(node, null, sourceInfo, ctx, span, exprInfo());
      return;
    }
    if (this.ts.isSpreadElement?.(node)) {
      this.activateSourceCallbackExpression(node.expression, ctx, span, sourceInfo);
      return;
    }
    if (this.ts.isObjectLiteralExpression?.(node)) {
      this.activateSourceObjectCallbacks(node, ctx, span, sourceInfo);
      return;
    }

    const info = this.bindingValueInfo(node, ctx, span);
    this.activateSourceCallbackInfo(info, ctx, span, sourceInfo);
    for (const ref of refsForReadExpr(this.ts, node, ctx, this.facts, this.index, { includePrefixes: false })) {
      this.activateSourceDescendantCallbacks(ref, ctx, span, sourceInfo);
    }
  }
  activateSourceObjectCallbacks(objectLiteral, ctx, span, sourceInfo) {
    for (const property of objectLiteral.properties || []) {
      if (this.ts.isSpreadAssignment?.(property)) {
        const spreadInfo = this.spreadDescendantFieldInfo(property.expression, ctx, span);
        this.activateSourceCallbackInfo(spreadInfo, ctx, span, sourceInfo);
        this.activateSourceCallbackExpression(property.expression, ctx, span, sourceInfo);
        continue;
      }
      const value = objectLiteralPropertyValue(this.ts, property);
      if (!value) continue;
      this.activateSourceCallbackExpression(value, ctx, span, sourceInfo);
    }
  }
  activateSourceCallbackInfo(info, ctx, span, sourceInfo) {
    for (const alias of info.aliases || []) {
      const target = this.functionsByKey.get(alias);
      if (!target) continue;
      this.recordCall(callFact(ctx.info.key, target.key, span));
      this.seedCallbackTargetArguments(target, null, sourceInfo, span);
    }
    for (const fieldInfo of info.fieldInfos?.values?.() || []) {
      this.activateSourceCallbackInfo(fieldInfo, ctx, span, sourceInfo);
    }
  }
  activateSourceDescendantCallbacks(baseRef, ctx, span, sourceInfo) {
    this.recordDescendantRefRead(baseRef, ctx.info.key);
    for (const { ref } of this.facts.descendantRefsOf(baseRef)) {
      const info = exprInfo();
      this.mergeRefFacts(info, ref);
      this.activateSourceCallbackInfo(info, ctx, span, sourceInfo);
    }
  }
  analyzeInlineCallback(callback, paramIndexes, sourceInfo, ownerCtx, callSpan) {
    const info = this.inlineCallbackInfo(callback, ownerCtx, callSpan);
    this.functionsByKey.set(info.key, info);
    const callbackCtx = this.makeContext(info, ownerCtx.control_origin);
    const actualInfosByParam = new Map();
    for (const paramIndex of callbackParamIndexes(paramIndexes, callback.parameters?.length || 0)) {
      const param = (callback.parameters || [])[paramIndex];
      if (!param) continue;
      const paramName = classMemberName(this.ts, param.name);
      if (!paramName) continue;
      this.seedFormalInput(info.key, paramName, sourceInfo, callSpan, actualInfosByParam);
    }

    if (this.ts.isBlock(callback.body)) {
      this.analyzeBlock(callback.body.statements, callbackCtx);
    } else {
      const bodySpan = this.markSpan(info, callback.body);
      const bodyInfo = this.bindingValueInfo(callback.body, callbackCtx, bodySpan);
      this.propagateReturn(bodyInfo, callbackCtx, bodySpan);
    }
    return { info, actualInfosByParam };
  }
  scanSourceBearingInlineCallbacks(call, ctx, span) {
    for (const callback of inlineCallbacksInCallArguments(this.ts, call)) {
      if (!this.inlineCallbackMayContainSource(callback, ctx, span)) continue;
      this.analyzeSourceBearingInlineCallback(callback, ctx, span);
    }
  }
  analyzeSourceBearingInlineCallback(callback, ctx, span) {
    this.inlineFunctionValueScanDepth += 1;
    try {
      return this.analyzeInlineCallback(callback, [], exprInfo(), ctx, span);
    } finally {
      this.inlineFunctionValueScanDepth -= 1;
    }
  }
  inlineCallbackMayContainSource(callback, ctx, span) {
    if (this.inlineSourceHits.has(callback)) return true;
    if (this.inlineSourceTextMisses.has(callback)) return false;
    if (!callbackTextMayContainSource(callback.getText(ctx.info.sourceFile), this.inlineSourceTokenSpecs)) {
      this.inlineSourceTextMisses.add(callback);
      return false;
    }

    let found = false;
    const visit = (node) => {
      if (found) return;
      const expr = unwrapTsExpression(this.ts, node);
      if (
        expr &&
        (this.ts.isCallExpression(expr) || this.ts.isNewExpression(expr)) &&
        providerRequestCall(this.ts, expr, ctx, this.facts, this.index, this.sourceRules).size
      ) {
        found = true;
        return;
      }
      this.ts.forEachChild(node, visit);
    };
    visit(callback);
    if (!found) found = this.inlineCallbackHasLocalEndpointSource(callback, ctx, span);
    if (found) this.inlineSourceHits.add(callback);
    return found;
  }
  inlineCallbackHasLocalEndpointSource(callback, ownerCtx, span) {
    const info = this.inlineCallbackInfo(callback, ownerCtx, span);
    const ctx = this.makeContext(info);
    const facts = new FactStore();
    let found = false;

    const visit = (node) => {
      if (found || (node !== callback && isFunctionLikeWithBody(this.ts, node))) return;
      if (this.ts.isVariableDeclaration(node) && this.ts.isIdentifier(node.name) && node.initializer) {
        const value = unwrapTsExpression(this.ts, node.initializer);
        facts.addString(
          localRef(info.key, node.name.text),
          stringFragmentsForExpression(this.ts, value, this.sourceRules),
        );
      }
      const expr = unwrapTsExpression(this.ts, node);
      if (
        expr &&
        (this.ts.isCallExpression(expr) || this.ts.isNewExpression(expr)) &&
        providerRequestCall(this.ts, expr, ctx, facts, this.index, this.sourceRules).size
      ) {
        found = true;
        return;
      }
      this.ts.forEachChild(node, visit);
    };
    visit(callback);
    return found;
  }
  inlineCallbackInfo(callback, ownerCtx, callSpan) {
    const owner = ownerCtx.info;
    const qualname = `${owner.qualname || owner.name || owner.key}.<callback>@${callSpan.start_line}:${callSpan.end_line}`;
    const key = `${owner.key}::${qualname}`;
    this.syntheticFunctionOwners.set(key, owner.key);
    return {
      key,
      file: owner.file,
      node: callback,
      sourceFile: owner.sourceFile,
      text: owner.text,
      name: "<callback>",
      registerPath: "",
      kind: "inline_callback",
      qualname,
      scope: owner.scope,
      parentScope: owner.scope,
      classKey: owner.classKey,
      enclosingClassKey: owner.enclosingClassKey,
      enclosingFunction: owner.key,
      enclosingFunctions: [...(owner.enclosingFunctions || []), owner.key],
      start: callSpan.start_line,
      end: callSpan.end_line,
      span: callSpan,
      params: functionParams(this.ts, callback, owner.sourceFile),
      returnAnnotation: callback.type ? callback.type.getText(owner.sourceFile) : "",
      assignedNames: collectAssignedNames(this.ts, callback),
      declaredNames: collectDeclaredNames(this.ts, callback),
    };
  }
  resolveCallbackTargets(callback, ctx) {
    if (!callback) return [];
    const out = new Map();
    const direct = this.index.functionByNode?.get(callback);
    if (direct) out.set(direct.key, direct);
    for (const ref of refsForReadExpr(this.ts, callback, ctx, this.facts, this.index, { includePrefixes: false })) {
      for (const alias of this.facts.aliasOf(ref)) {
        const info = this.functionsByKey.get(alias);
        if (info) out.set(info.key, info);
      }
    }
    for (const resolved of resolveExprName(this.ts, callback, ctx.info.scope, this.index)) {
      if (!resolved.function) continue;
      const info = this.functionsByKey.get(resolved.function);
      if (info) out.set(info.key, info);
    }
    return [...out.values()];
  }
  seedCallbackTargetArguments(target, paramIndexes, sourceInfo, span) {
    const actualInfosByParam = new Map();
    for (const paramIndex of callbackParamIndexes(paramIndexes, target.params.length)) {
      const param = target.params[paramIndex];
      if (!param) continue;
      this.seedFormalInput(target.key, param.name, sourceInfo, span, actualInfosByParam);
    }
    return actualInfosByParam;
  }
  handleEventPublishFlow(call, ctx, span, argInfos) {
    const callee = unwrapTsExpression(this.ts, call.expression);
    if (!this.ts.isPropertyAccessExpression(callee) && !this.ts.isElementAccessExpression(callee)) return;
    if (!EVENT_PUBLISH_METHODS.has(this.callbackMethodName(callee))) return;

    const payloadInfo = exprInfo();
    for (const argInfo of argInfos) mergeTaintFacts(payloadInfo, argInfo);
    if (!payloadInfo.origins.size) return;

    for (const ref of this.eventChannelPayloadRefs(callee.expression, ctx, { write: true })) {
      this.addInfoToRef(ref, payloadInfo, span, { taint: true });
    }
    this.facts.addDataEdge(span, edgeOrigins(payloadInfo), "assignment");
  }
  applyEventSubscriptionFlow(call, ctx, span, receiverInfo, calleeInfo, result) {
    const callee = unwrapTsExpression(this.ts, call.expression);
    const callbackArgIndex = this.eventHandlerArgumentIndex(call, ctx);
    if (callbackArgIndex < 0) return;
    const channelInfo = this.eventChannelPayloadInfo(callee, ctx);
    const sourceInfo = this.eventSubscriptionSourceInfo(callee, receiverInfo, calleeInfo, channelInfo);
    if (!sourceInfo.origins.size) return;
    const callback = (call.arguments || [])[callbackArgIndex];
    if (!callback || this.ts.isSpreadElement?.(callback)) return;
    this.facts.addDataEdge(span, edgeOrigins(sourceInfo), "caller");
    this.activateCallback(callback, null, sourceInfo, ctx, span, result);
  }
  eventSubscriptionSourceInfo(callee, receiverInfo, calleeInfo, channelInfo) {
    if (channelInfo.origins.size) return channelInfo;
    if (this.isEventSubscriptionCallee(callee) && receiverInfo.origins.size) return receiverInfo;
    if (calleeInfo.origins.size) return calleeInfo;
    return exprInfo();
  }
  eventChannelPayloadInfo(callee, ctx) {
    if (!this.ts.isPropertyAccessExpression(callee) && !this.ts.isElementAccessExpression(callee)) return exprInfo();
    return this.readRefFacts(
      this.eventChannelPayloadRefs(callee.expression, ctx, { write: false }), ctx.info.key,
    );
  }
  eventChannelPayloadRefs(receiver, ctx, { write }) {
    const baseRefs = write
      ? targetRefs(this.ts, receiver, ctx, this.facts, this.index)
      : refsForReadExpr(this.ts, receiver, ctx, this.facts, this.index, { includePrefixes: false });
    const refs = baseRefs.map((ref) => appendRefPath(ref, CHANNEL_PAYLOAD_FIELD));
    for (const typeId of this.receiverTypeIds(receiver, ctx)) {
      refs.push(classFieldRef(typeId, CHANNEL_PAYLOAD_FIELD));
    }
    return uniqueBy(refs, refKey);
  }
  receiverTypeIds(receiver, ctx) {
    const out = new Set();
    for (const ref of refsForReadExpr(this.ts, receiver, ctx, this.facts, this.index, { includePrefixes: false })) {
      this.recordRefRead(ref, ctx.info.key);
      mergeInto(out, this.facts.typeOf(ref));
    }
    return out;
  }
  isEventSubscriptionCallee(callee) {
    if (this.ts.isPropertyAccessExpression(callee)) return EVENT_SUBSCRIPTION_METHODS.has(callee.name.text);
    if (this.ts.isElementAccessExpression(callee)) {
      const arg = callee.argumentExpression;
      return Boolean(arg && this.ts.isStringLiteralLike(arg) && EVENT_SUBSCRIPTION_METHODS.has(arg.text));
    }
    return false;
  }
  eventHandlerArgumentIndex(call, ctx) {
    const args = [...(call.arguments || [])];
    for (let index = args.length - 1; index >= 0; index -= 1) {
      const arg = unwrapTsExpression(this.ts, args[index]);
      if (isFunctionLikeWithBody(this.ts, arg)) return index;
      if (this.resolveCallbackTargets(arg, ctx).length) return index;
    }
    const callee = unwrapTsExpression(this.ts, call.expression);
    const method = this.callbackMethodName(callee);
    if (method === "subscribe" && args.length) return 0;
    if (args.length >= 2) return 1;
    return -1;
  }
  callReceiverInfo(call, ctx, span) {
    const callee = unwrapTsExpression(this.ts, call.expression);
    if (this.ts.isPropertyAccessExpression(callee) || this.ts.isElementAccessExpression(callee)) {
      return this.evalExpr(callee.expression, ctx, span);
    }
    return exprInfo();
  }
  callCalleeInfo(call, ctx) {
    const callee = unwrapTsExpression(this.ts, call.expression);
    return this.readRefFacts(
      refsForReadExpr(this.ts, callee, ctx, this.facts, this.index, { includePrefixes: true }), ctx.info.key,
    );
  }
  readRefFacts(refs, functionId) {
    const info = exprInfo();
    for (const ref of refs) {
      this.recordRefRead(ref, functionId);
      this.mergeRefFacts(info, ref);
    }
    return info;
  }
  mergeReturnFacts(result, functionId) {
    this.mergeRefFacts(result, returnRef(functionId));
  }
  mergeReturnFieldFacts(result, functionId) {
    for (const { ref, suffix } of this.facts.descendantRefsOf(returnRef(functionId))) {
      const fieldInfo = exprInfo();
      this.mergeRefFacts(fieldInfo, ref);
      if (infoHasFacts(fieldInfo)) mergeFieldInfo(result, suffix, fieldInfo);
    }
  }
  mergeRefFacts(target, ref) {
    mergeInto(target.origins, this.facts.taintOf(ref));
    mergeInto(target.paramOrigins, this.facts.paramTaintOf(ref));
    mergeInto(target.providers, this.facts.providerOf(ref));
    mergeInto(target.types, this.facts.typeOf(ref));
    mergeInto(target.aliases, this.facts.aliasOf(ref));
    mergeInto(target.paramDeps, this.facts.paramDepOf(ref));
    mergeInto(target.strings, this.facts.stringOf(ref));
  }
  enqueueChangedRefs(queue, options = {}) {
    enqueueChangedRefs({
      queue,
      refs: this.facts.drainChangedRefs(),
      callersByCallee: this.callersByCallee,
      localRefReaders: this.localRefReaders,
      classFieldReaders: this.classFieldReaders,
      moduleRefReaders: this.moduleRefReaders,
      descendantRefReaders: this.descendantRefReaders,
      ignoreLocalFunction: options.ignoreLocalFunction,
    });
  }
  recordCall(fact) {
    const added = recordCallEdge({
      facts: this.facts,
      callersByCallee: this.callersByCallee,
      fact,
    });
    const owner = this.syntheticFunctionOwners.get(fact.caller);
    if (owner) {
      recordCallEdge({
        facts: this.facts,
        callersByCallee: this.callersByCallee,
        fact: { ...fact, caller: owner },
      });
    }
    return added;
  }
  recordRefRead(ref, functionId) {
    if (ref.kind === "local") {
      recordReader(this.localRefReaders, ref, functionId);
    } else if (ref.kind === "class_field") {
      recordReader(this.classFieldReaders, ref, functionId);
    } else if (ref.kind === "module") {
      recordReader(this.moduleRefReaders, ref, functionId);
    }
  }
  recordDescendantRefRead(ref, functionId) {
    recordReader(this.descendantRefReaders, ref, functionId);
  }
  seedCalleeArguments(target, receiverInfo, argInfos, call, ctx, span) {
    const actualInfosByParam = new Map();
    const callee = this.index.functions.get(target.key);
    if (!callee) return actualInfosByParam;
    if (infoHasFacts(receiverInfo)) {
      this.seedFormalInput(callee.key, "this", receiverInfo, span, actualInfosByParam);
    }
    const params = callee.params.map((param) => param.name);
    for (let index = 0; index < argInfos.length; index += 1) {
      const argInfo = argInfos[index];
      if (this.ts.isSpreadElement?.(call.arguments[index])) {
        for (const param of params.slice(index)) {
          this.seedFormalInput(callee.key, param, argInfo, span, actualInfosByParam);
        }
      } else if (index < params.length) {
        const paramRef = localRef(callee.key, params[index]);
        this.seedFormalInput(callee.key, params[index], argInfo, span, actualInfosByParam);
        this.copyActualFieldFacts(call.arguments[index], paramRef, ctx, span, callee.key, params[index], actualInfosByParam);
        this.propagateCallObjectArgumentFields(call.arguments[index], callee.key, params[index], ctx, span, actualInfosByParam);
      }
    }
    return actualInfosByParam;
  }
  seedFormalInput(functionId, name, actualInfo, span, actualInfosByParam) {
    if (!infoHasFacts(actualInfo)) return;
    if (actualInfo.origins.size) this.facts.addBridgeEdge(span, edgeOrigins(actualInfo), "caller");
    if (!actualInfosByParam.has(name)) actualInfosByParam.set(name, []);
    actualInfosByParam.get(name).push(actualInfo);
    const formalRef = localRef(functionId, name);
    const formalInfo = this.formalInputInfo(functionId, name, actualInfo);
    this.addInfoToRef(formalRef, formalInfo, span, { taint: true });
    this.addFieldInfosToRef(formalRef, formalInfo, span, { taint: true });
  }
  formalInputInfo(functionId, name, actualInfo) {
    const info = this.formalInputFieldInfo(functionId, name, actualInfo);
    for (const [suffix, fieldInfo] of actualInfo.fieldInfos || []) {
      if (!infoHasCapabilityFacts(fieldInfo)) continue;
      mergeFieldInfo(info, suffix, this.formalInputFieldInfo(functionId, appendGeneratedPath(name, suffix), fieldInfo));
    }
    return info;
  }
  formalInputFieldInfo(functionId, name, actualInfo) {
    const info = exprInfo();
    copyFormalInputFacts(info, actualInfo);
    info.paramDeps.add(paramDep(functionId, name));
    return info;
  }
  copyActualFieldFacts(actualExpr, formalRef, callerCtx, span, functionId = "", formalPath = "", actualInfosByParam = null) {
    const sourceRefs = refsForReadExpr(this.ts, actualExpr, callerCtx, this.facts, this.index, { includePrefixes: false });
    for (const sourceBaseRef of sourceRefs) {
      for (const { ref: sourceRef, suffix } of this.facts.descendantRefsOf(sourceBaseRef)) {
        this.recordRefRead(sourceRef, callerCtx.info.key);
        const info = exprInfo();
        this.mergeRefFacts(info, sourceRef);
        if (!infoHasFacts(info)) continue;
        if (functionId && formalPath && actualInfosByParam) {
          this.seedFormalInput(functionId, appendGeneratedPath(formalPath, suffix), info, span, actualInfosByParam);
        } else {
          this.addInfoToRef(
            appendRefPath(formalRef, suffix),
            info,
            span,
            { taint: true },
          );
        }
      }
    }
  }
  instantiateReturnParamDeps(functionId, actualInfosByParam) {
    const result = exprInfo();
    for (const { dep, spans } of this.facts.returnParamDepsOf(functionId).values()) {
      if (dep.function !== functionId) continue;
      for (const actualInfo of actualInfosByParam.get(dep.name) || []) {
        mergeInto(result.paramDeps, actualInfo.paramDeps);
        if (!actualInfo.origins.size) continue;
        mergeInto(result.origins, spans);
        if (this.isParamOnlyValue(actualInfo, actualInfo.paramDeps)) mergeInto(result.paramOrigins, spans);
      }
    }
    return result;
  }
  instantiateReturnFieldParamDeps(result, functionId, actualInfosByParam) {
    for (const { ref, suffix } of this.facts.descendantRefsOf(returnRef(functionId))) {
      const fieldTemplate = exprInfo();
      this.mergeRefFacts(fieldTemplate, ref);
      const fieldResult = exprInfo();
      for (const dep of fieldTemplate.paramDeps || []) {
        if (dep.function !== functionId) continue;
        for (const actualInfo of actualInfosByParam.get(dep.name) || []) {
          mergeExprInfo(fieldResult, actualInfo);
          for (const alias of actualInfo.aliases || []) this.mergeReturnFacts(fieldResult, alias);
        }
      }
      if (infoHasCapabilityFacts(fieldResult)) mergeFieldInfo(result, suffix, fieldResult);
    }
  }
  propagateCallObjectArgumentFields(argument, functionId, formalPath, ctx, span, actualInfosByParam) {
    const value = unwrapTsExpression(this.ts, argument);
    if (value && this.ts.isObjectLiteralExpression?.(value)) {
      this.seedFormalObjectLiteralFields(value, functionId, formalPath, ctx, span, actualInfosByParam);
    }
  }
  seedFormalObjectLiteralFields(objectLiteral, functionId, formalPath, ctx, span, actualInfosByParam) {
    for (const property of objectLiteral.properties || []) {
      const field = objectLiteralFieldName(this.ts, property);
      const initializer = objectLiteralPropertyValue(this.ts, property);
      if (!field || !initializer) continue;
      const fieldPath = appendGeneratedPath(formalPath, field);
      const fieldInfo = this.bindingValueInfo(initializer, ctx, span);
      this.seedFormalInput(functionId, fieldPath, fieldInfo, span, actualInfosByParam);
      this.copyActualFieldFacts(
        initializer,
        localRef(functionId, fieldPath),
        ctx,
        span,
        functionId,
        fieldPath,
        actualInfosByParam,
      );
      const nested = unwrapTsExpression(this.ts, initializer);
      if (nested && this.ts.isObjectLiteralExpression?.(nested)) {
        this.seedFormalObjectLiteralFields(nested, functionId, fieldPath, ctx, span, actualInfosByParam);
      }
    }
  }
  callReturnsReceiverTaint(call) {
    const callee = unwrapTsExpression(this.ts, call.expression);
    if (!this.ts.isPropertyAccessExpression(callee)) return false;
    return RECEIVER_RETURN_METHODS.has(callee.name.text);
  }
  callReturnsPromiseCombinatorTaint(call) {
    const path = exprPath(this.ts, unwrapTsExpression(this.ts, call.expression));
    return (
      path === "Promise.race" ||
      path === "Promise.any" ||
      path === "Promise.all" ||
      path === "Promise.allSettled"
    );
  }
  handleIfStatement(stmt, ctx, span) {
    const controlInfo = this.evalExpr(stmt.expression, ctx, span);
    this.enterControlBlocks(controlInfo, span, ctx, stmt.thenStatement, stmt.elseStatement);
  }
  handleLoopStatement(stmt, ctx, span) {
    const controlInfo = this.evalExpr(stmt.expression, ctx, span);
    this.enterControlBlocks(controlInfo, span, ctx, stmt.statement);
  }
  handleForStatement(stmt, ctx, span) {
    if (stmt.initializer) this.analyzeForInitializer(stmt.initializer, ctx, span);
    const controlInfo = this.evalExpr(stmt.condition, ctx, span);
    this.evalExpr(stmt.incrementor, ctx, span);
    this.enterControlBlocks(controlInfo, span, ctx, stmt.statement);
  }
  handleForEachStatement(stmt, ctx, span) {
    const iterInfo = this.bindingValueInfo(stmt.expression, ctx, span);
    if (this.ts.isVariableDeclarationList(stmt.initializer)) {
      for (const declaration of stmt.initializer.declarations || []) {
        this.propagateAssignment(iterInfo, [declaration.name], ctx, span);
      }
    } else {
      this.propagateAssignment(iterInfo, [stmt.initializer], ctx, span);
    }
    this.enterControlBlocks(iterInfo, span, ctx, stmt.statement);
  }
  handleSwitchStatement(stmt, ctx, span) {
    const controlInfo = this.evalExpr(stmt.expression, ctx, span);
    if (controlInfo.origins.size) this.facts.addBridgeEdge(span, edgeOrigins(controlInfo), "control");
    const nextCtx = this.controlContext(controlInfo, span, ctx);
    for (const clause of stmt.caseBlock.clauses || []) {
      if (clause.expression) this.evalExpr(clause.expression, ctx, span);
      this.analyzeBlock(clause.statements, nextCtx);
    }
  }
  handleTryStatement(stmt, ctx, span) {
    this.analyzeBlock(stmt.tryBlock.statements, ctx);
    if (stmt.catchClause) {
      if (stmt.catchClause.variableDeclaration) {
        this.propagateAssignment(exprInfo(), [stmt.catchClause.variableDeclaration.name], ctx, span);
      }
      this.analyzeBlock(stmt.catchClause.block.statements, ctx);
    }
    if (stmt.finallyBlock) this.analyzeBlock(stmt.finallyBlock.statements, ctx);
  }
  handleFallbackStatement(stmt, ctx, span) {
    for (const expr of expressionChildren(this.ts, stmt)) this.evalExpr(expr, ctx, span);
  }
  analyzeForInitializer(initializer, ctx, span) {
    if (this.ts.isVariableDeclarationList(initializer)) {
      for (const declaration of initializer.declarations || []) {
        const valueInfo = this.bindingValueInfo(declaration.initializer, ctx, span);
        this.propagateAssignment(valueInfo, [declaration.name], ctx, span);
      }
    } else {
      this.evalExpr(initializer, ctx, span);
    }
  }
  enterControlBlocks(controlInfo, span, ctx, ...blocks) {
    if (controlInfo.origins.size) this.facts.addDataEdge(span, edgeOrigins(controlInfo), "control");
    const nextCtx = this.controlContext(controlInfo, span, ctx);
    for (const block of blocks.filter(Boolean)) {
      if (this.ts.isBlock(block)) this.analyzeBlock(block.statements, nextCtx);
      else this.analyzeStatement(block, nextCtx);
    }
  }
  controlContext(controlInfo, span, ctx) {
    return controlInfo.origins.size ? this.makeContext(ctx.info, span) : ctx;
  }
  addDerivedTaint(target, span, sourceInfo) {
    target.origins.add(span);
    mergeSpanOrigins(target.predecessors, edgeOrigins(sourceInfo));
    if (!this.isParamOnlyValue(sourceInfo, sourceInfo.paramDeps)) return;
    target.paramOrigins.add(span);
    mergeInto(target.paramDeps, sourceInfo.paramDeps);
  }
  currentParamDeps(info, functionId) {
    return new Set([...info.paramDeps].filter((dep) => dep.function === functionId));
  }
  isParamOnlyValue(info, deps) {
    return Boolean(deps?.size) && setIsSubset(info.origins, info.paramOrigins);
  }
}
function orderedFunctions(index) {
  return [...index.functions.values()].sort(
    (left, right) => left.file.localeCompare(right.file) || left.qualname.localeCompare(right.qualname),
  );
}
function orderedClasses(index) {
  return [...index.classes.values()].sort(
    (left, right) => left.file.localeCompare(right.file) || left.qualname.localeCompare(right.qualname),
  );
}
function mergeFunctionBatches(currentBatch, dirtyBatch) {
  const seen = new Set(currentBatch);
  const out = [...currentBatch];
  for (const functionId of dirtyBatch) {
    if (seen.has(functionId)) continue;
    seen.add(functionId);
    out.push(functionId);
  }
  return out;
}
function callbackParamIndexes(paramIndexes, count) {
  if (Array.isArray(paramIndexes)) return paramIndexes;
  return Array.from({ length: count }, (_, index) => index);
}
function inlineCallbacksInCallArguments(ts, call) {
  const out = [];
  for (const arg of call.arguments || []) collectInlineCallbacks(ts, arg, out);
  return out;
}
function collectInlineCallbacks(ts, node, out) {
  const expr = unwrapTsExpression(ts, node);
  if (!expr || ts.isSpreadElement?.(expr)) return;
  if (isFunctionLikeWithBody(ts, expr)) {
    out.push(expr);
    return;
  }
  ts.forEachChild(expr, (child) => collectInlineCallbacks(ts, child, out));
}
function buildInlineSourceTokenSpecs(sourceRules) {
  const specs = [];
  for (const rule of sourceRules || []) {
    if (rule.module && rule.symbol) addTokenSpec(specs, symbolTokenParts(rule.symbol));
    for (const pattern of rule.endpoint_patterns || []) addTokenSpec(specs, endpointPatternTokenParts(pattern));
    for (const transport of rule.endpoint_transports || []) {
      addTokenSpec(specs, [String(transport.callee || "").split(".").at(-1)]);
    }
  }
  return specs;
}
function callbackTextMayContainSource(text, tokenSpecs) {
  const lower = String(text || "").toLowerCase();
  return tokenSpecs.some((tokens) => tokens.every((token) => lower.includes(token)));
}
function addTokenSpec(specs, tokens) {
  const normalized = [...new Set(tokens.map((token) => token.toLowerCase()).filter(Boolean))];
  if (normalized.length) specs.push(normalized);
}
function symbolTokenParts(symbol) {
  return String(symbol || "")
    .split(/[^A-Za-z0-9_$]+/)
    .map((part) => part.replace(/^\$+|\$+$/g, ""))
    .filter((part) => part.length >= 4 && !SOURCE_TOKEN_STOP_WORDS.has(part.toLowerCase()));
}
function endpointPatternTokenParts(pattern) {
  return String(pattern || "")
    .split(/[^A-Za-z0-9]+/)
    .filter((part) => part.length >= 4 && !SOURCE_TOKEN_STOP_WORDS.has(part.toLowerCase()));
}
function typeNamesInAnnotation(annotation) {
  const out = new Set();
  for (const match of String(annotation || "").matchAll(/\b[A-Za-z_$][A-Za-z0-9_$]*\b/g)) {
    const name = match[0];
    if (!TYPE_NAME_STOP_WORDS.has(name)) out.add(name);
  }
  return out;
}
function valueSelectingBinaryOperators(ts) {
  return new Set([
    ts.SyntaxKind.QuestionQuestionToken,
    ts.SyntaxKind.BarBarToken,
    ts.SyntaxKind.AmpersandAmpersandToken,
  ].filter((kind) => kind !== undefined));
}
function objectLiteralFieldName(ts, property) {
  if (ts.isPropertyAssignment?.(property) || ts.isShorthandPropertyAssignment?.(property) || ts.isMethodDeclaration?.(property)) {
    return classMemberName(ts, property.name);
  }
  return "";
}
function objectLiteralPropertyValue(ts, property) {
  if (ts.isPropertyAssignment?.(property)) return property.initializer;
  if (ts.isShorthandPropertyAssignment?.(property)) return property.name;
  if (ts.isMethodDeclaration?.(property)) return property;
  return null;
}
function bindingElementFieldName(ts, element) {
  if (element.propertyName) return classMemberName(ts, element.propertyName);
  return classMemberName(ts, element.name);
}
function isParameterProperty(ts, param) {
  return (param.modifiers || []).some((modifier) =>
    modifier.kind === ts.SyntaxKind.PublicKeyword ||
    modifier.kind === ts.SyntaxKind.PrivateKeyword ||
    modifier.kind === ts.SyntaxKind.ProtectedKeyword ||
    modifier.kind === ts.SyntaxKind.ReadonlyKeyword
  );
}
function moduleTargetRefs(ts, target, file) {
  const node = unwrapTsExpression(ts, target);
  if (!node) return [];
  if (ts.isIdentifier(node)) return [moduleRef(file, node.text)];
  if (ts.isObjectBindingPattern?.(node) || ts.isArrayBindingPattern?.(node)) {
    const refs = [];
    for (const element of node.elements || []) {
      if (!element || !ts.isBindingElement?.(element)) continue;
      refs.push(...moduleTargetRefs(ts, element.name, file));
    }
    return uniqueBy(refs, refKey);
  }
  const path = exprPath(ts, node);
  return path ? [moduleRef(file, path)] : [];
}
function infoHasFacts(info) {
  return (
    info.origins.size ||
    info.predecessors.size ||
    info.paramOrigins.size ||
    info.providers.size ||
    info.types.size ||
    info.aliases.size ||
    info.paramDeps.size ||
    info.strings.size ||
    info.fieldInfos?.size
  );
}
function infoHasCapabilityFacts(info) {
  if (
    info.providers.size ||
    info.aliases.size
  ) {
    return true;
  }
  for (const fieldInfo of info.fieldInfos?.values?.() || []) {
    if (infoHasCapabilityFacts(fieldInfo)) return true;
  }
  return false;
}
function mergeTaintFacts(target, source) {
  mergeInto(target.origins, source.origins);
  mergeInto(target.predecessors, source.predecessors);
  mergeInto(target.paramOrigins, source.paramOrigins);
  mergeInto(target.paramDeps, source.paramDeps);
  return target;
}
function copyFormalInputFacts(target, source) {
  mergeInto(target.origins, source.origins);
  mergeInto(target.paramOrigins, source.origins);
  mergeInto(target.providers, source.providers);
  mergeInto(target.types, source.types);
  mergeInto(target.aliases, source.aliases);
  mergeInto(target.strings, source.strings);
  return target;
}
function setIsSubset(left, right) {
  const rightKeys = new Set(Array.from(right || []).map(setItemKey));
  for (const item of left || []) {
    if (!rightKeys.has(setItemKey(item))) return false;
  }
  return true;
}
function setItemKey(item) {
  if (
    item &&
    typeof item === "object" &&
    item.filepath &&
    item.start_line !== undefined &&
    item.end_line !== undefined
  ) {
    return spanKey(item);
  }
  if (item && typeof item === "object") return JSON.stringify(item);
  return `${typeof item}:${item}`;
}
function edgeOrigins(info) {
  if (!info.predecessors?.size) return info.origins;
  if (!info.origins?.size) return info.predecessors;
  const origins = new Set();
  mergeSpanOrigins(origins, info.origins);
  mergeSpanOrigins(origins, info.predecessors);
  return origins;
}
function mergeSpanOrigins(target, values) {
  const keys = new Set([...target].map(spanKey));
  for (const value of values || []) {
    const key = spanKey(value);
    if (keys.has(key)) continue;
    keys.add(key);
    target.add(value);
  }
  return target;
}
function transportNameMatchesSuffix(path, suffix) {
  return Boolean(path && (path === suffix || path.endsWith(`.${suffix}`)));
}
function storedContainerValueInfos(method, argInfos) {
  if (method === "set") return argInfos.slice(1, 2);
  if (method === "append") return argInfos.length > 1 ? argInfos.slice(1, 2) : argInfos.slice(0, 1);
  if (method === "fill" || method === "add") return argInfos.slice(0, 1);
  if (method === "splice") return argInfos.slice(2);
  return argInfos;
}
function appendRefPath(ref, suffix) {
  const path = appendGeneratedPath("path" in ref ? ref.path : "", suffix);
  if (ref.kind === "local") return localRef(ref.function, path);
  if (ref.kind === "return") return returnRef(ref.function, path);
  if (ref.kind === "class_field") return classFieldRef(ref.class, path);
  if (ref.kind === "module") return moduleRef(ref.file, path);
  return ref;
}
function appendGeneratedPath(basePath, suffix) {
  const parts = `${basePath || ""}.${suffix || ""}`.split(".").filter(Boolean);
  const out = [];
  for (const part of parts) {
    if (part === DEEP_OBJECT_FIELD) break;
    if (part === DYNAMIC_OBJECT_FIELD && out.at(-1) === DYNAMIC_OBJECT_FIELD) continue;
    if (out.length >= MAX_GENERATED_REF_PATH_SEGMENTS) {
      out.push(DEEP_OBJECT_FIELD);
      break;
    }
    out.push(part);
  }
  return out.join(".");
}
function stringFragmentsForExpression(ts, node, sourceRules) {
  const out = new Set();
  if (!node) return out;
  node = unwrapTsExpression(ts, node);
  if (ts.isStringLiteralLike?.(node) || ts.isNoSubstitutionTemplateLiteral?.(node)) {
    addEndpointString(out, node.text, sourceRules);
  } else if (ts.isTemplateExpression?.(node)) {
    addEndpointString(out, templateStaticText(node), sourceRules);
  } else if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.PlusToken) {
    for (const left of stringFragmentsForExpression(ts, node.left, sourceRules)) {
      for (const right of stringFragmentsForExpression(ts, node.right, sourceRules)) {
        addEndpointString(out, `${left}${right}`, sourceRules);
      }
    }
  }
  return out;
}
function standardUrlConstructorArgument(ts, expression) {
  let node = unwrapTsExpression(ts, expression);
  if (
    ts.isCallExpression(node) &&
    node.arguments.length === 0 &&
    ts.isPropertyAccessExpression(node.expression) &&
    node.expression.name.text === "toString"
  ) {
    node = unwrapTsExpression(ts, node.expression.expression);
  }
  if (!ts.isNewExpression(node)) return null;
  const callee = unwrapTsExpression(ts, node.expression);
  const isStandardUrl =
    (ts.isIdentifier(callee) && callee.text === "URL") ||
    (ts.isPropertyAccessExpression(callee) &&
      ts.isIdentifier(callee.expression) &&
      callee.expression.text === "globalThis" &&
      callee.name.text === "URL");
  return isStandardUrl ? node.arguments?.[0] || null : null;
}
function templateStaticText(node) {
  return [
    node.head.text,
    ...node.templateSpans.map((span) => span.literal.text),
  ].join("");
}
function addEndpointString(out, text, sourceRules) {
  if (!isTypescriptEndpointLikeString(text, sourceRules)) return;
  out.add(text);
}
function recordReader(readersByRef, ref, functionId) {
  const key = refKey(ref);
  if (!readersByRef.has(key)) readersByRef.set(key, new Set());
  readersByRef.get(key).add(functionId);
}
