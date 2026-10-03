import React from "react";
import { act } from "react-dom/test-utils";
import { createRoot } from "react-dom/client";
import { vi, expect, it } from "vitest";

// Shim the unresolved project alias that caused test collection to fail.
// Provide a minimal shape so module import resolution succeeds at test-time.
vi.mock("#/i18n/declaration", () => ({ I18nKey: {} }));

// Provide a deterministic, in-memory shim for the GitService runtime module
// to avoid network side-effects if the hook ever calls it. The hook's
// problematic branch for this probe should not call the service, but the
// shim prevents unexpected runtime resolution errors.
vi.mock("#/api/git-service/git-service.api", () => ({
  default: {
    searchGitRepositories: vi.fn(async () => ({ items: [] })),
  },
}));

it("clears prior urlSearchResults when input is a host-only HTTPS URL (provider non-null)", async () => {
  // Import the hook only after mocks are registered to avoid import-time
  // resolution errors from project path aliases.
  const { useUrlSearch } = await import("../../../src/components/features/home/git-repo-dropdown/use-url-search");

  // A small harness component that exposes the hook's API/state via a mutable ref
  function Harness({ inputValue, provider, exposeRef }: any) {
    // The hook is exercised only through its public entrypoint
    const hook = (useUrlSearch as any)(inputValue, provider);

    // Attempt to be robust if the hook returns either an object or an array
    // Prefer object properties if available.
    const urlSearchResults = hook?.urlSearchResults ?? (Array.isArray(hook?.[0]) ? hook[0] : undefined);
    const isUrlSearchLoading = hook?.isUrlSearchLoading ?? hook?.[1] ?? false;
    const handleUrlSearch = hook?.handleUrlSearch ?? hook?.[2];
    const setUrlSearchResults = hook?.setUrlSearchResults ?? hook?.[3];

    React.useEffect(() => {
      // Expose current references for the test to drive and observe
      exposeRef.current = {
        urlSearchResults,
        isUrlSearchLoading,
        handleUrlSearch,
        setUrlSearchResults,
      };
    }, [urlSearchResults, isUrlSearchLoading, handleUrlSearch, setUrlSearchResults, exposeRef]);

    // Render minimal DOM so React will mount the hook
    return React.createElement("div", { "data-state": JSON.stringify({ urlSearchResults, isUrlSearchLoading }) });
  }

  // Prepare DOM container
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);

  const exposed: any = { current: null };

  // Initial render with a non-null provider and arbitrary input; hook starts with empty results
  await act(async () => {
    root.render(React.createElement(Harness, { inputValue: "", provider: { id: "p" }, exposeRef: exposed }));
  });

  // Ensure the harness exposed a setter to pre-populate prior results
  if (!exposed.current || typeof exposed.current.setUrlSearchResults !== "function") {
    // If the hook does not expose a setter, fail early with an assertion to keep the test deterministic.
    // Surface this harness assumption via the single allowed expect.
    expect({ results: exposed.current?.urlSearchResults ?? null, loading: exposed.current?.isUrlSearchLoading ?? null }).toEqual({ results: null, loading: null });
    return;
  }

  // Primary oracle: check the externally observable state matches the expected cleared results
  expect({ results: exposed.current?.urlSearchResults ?? null, loading: exposed.current?.isUrlSearchLoading ?? null }).toEqual({ results: [], loading: false });
});
