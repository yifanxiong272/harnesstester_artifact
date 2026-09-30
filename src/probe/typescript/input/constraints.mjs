/** Return prompt-visible constraints shared by both probing strategies. */
export function probeConstraints() {
  return [
    "Use only the buggy-side target units, existing test context, optional retrieved context, and constraints provided in the packet.",
    "Do not use issue text, PR text, commit messages, fixed source, source diffs, changed hunks, benchmark labels, manual review notes, or official triggering tests.",
    "Write append-only Vitest code under the generated_test_roots listed in the target packet.",
    "Use deterministic mocks or direct object construction.",
    "Do not use live model, provider, credential, or network behavior.",
    "Do not depend on unbounded wall-clock timing or inspect or mutate operating-system process state.",
    "Fake timers, bounded deterministic timing, and prompt-visible public project observation helpers are allowed when required by the target behavior.",
  ];
}
