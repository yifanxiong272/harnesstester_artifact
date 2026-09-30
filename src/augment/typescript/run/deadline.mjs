export class TimeBudgetExceeded extends Error {
  constructor() {
    super("run time budget exhausted");
    this.code = "time_budget";
  }
}

export function remainingBudgetMs(context) {
  if (typeof context.remainingTimeMs !== "function") {
    return Number.POSITIVE_INFINITY;
  }
  const remaining = Number(context.remainingTimeMs());
  if (remaining === Number.POSITIVE_INFINITY) {
    return remaining;
  }
  return Number.isFinite(remaining) ? Math.max(0, remaining) : 0;
}

export function requireBudget(context) {
  const remaining = remainingBudgetMs(context);
  if (remaining <= 0) {
    throw new TimeBudgetExceeded();
  }
  return remaining;
}

export async function withinBudget(context, operation) {
  const remaining = requireBudget(context);
  if (!Number.isFinite(remaining)) {
    return operation(null);
  }

  let timer;
  try {
    return await Promise.race([
      operation(Math.max(1, Math.floor(remaining))),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new TimeBudgetExceeded()), remaining);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}
