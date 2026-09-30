import path from "node:path";
import { AsyncLocalStorage } from "node:async_hooks";

import { writeJson } from "../support/json.mjs";

export const DEFAULT_CASE_TIME_BUDGET_SECONDS = 1800;

export class CaseBudgetExceeded extends Error {
  constructor(message = "case budget exhausted") {
    super(message);
    this.name = "CaseBudgetExceeded";
  }
}

export class CaseTimeBudgetExceeded extends CaseBudgetExceeded {
  constructor() {
    super("case time budget exhausted");
    this.name = "CaseTimeBudgetExceeded";
  }
}

const deadlineContext = new AsyncLocalStorage();

export function withCaseTimeBudget(runDir, seconds, operation) {
  let deadline = null;
  if (seconds > 0) {
    const recordPath = path.join(runDir, "time-budget.json");
    const startedAt = Date.now() / 1000;
    const record = { started_at: startedAt, deadline_at: startedAt + seconds };
    writeJson(recordPath, record);
    // Record wall-clock timestamps; enforce the shared deadline monotonically.
    deadline = performance.now() + (record.deadline_at * 1000 - Date.now());
  }
  return deadlineContext.run(deadline, () => {
    limitTimeout();
    return operation();
  });
}

export function limitTimeout(milliseconds = Infinity) {
  const deadline = deadlineContext.getStore();
  if (deadline == null) {
    return milliseconds;
  }
  const remaining = deadline - performance.now();
  if (remaining <= 0) {
    throw new CaseTimeBudgetExceeded();
  }
  return Math.min(milliseconds, remaining);
}
