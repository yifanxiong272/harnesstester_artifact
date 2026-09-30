import { it, expect } from "vitest";
import { markdownToSignalText } from "../../signal/format";

it("preserves bold style ranges for link labels when URLs are appended", () => {
  const md = "See [**boldlabel**](https://a.example) and [**other**](https://b.example)";
  const res = markdownToSignalText(md);
  const txt: string = res.text;

  const boldSubstrings = (res.styles ?? [])
    .filter(s => s.style === "BOLD")
    .map(s => {
      const start: number = (s as any).start;
      const length: number = typeof (s as any).length === "number"
        ? (s as any).length
        : (typeof (s as any).end === "number" ? (s as any).end - (s as any).start : 0);
      return txt.slice(start, start + length);
    });

  expect(boldSubstrings).toEqual(["boldlabel", "other"]);
});
