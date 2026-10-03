import { it, expect } from "vitest";
import { stripModelSpecialTokens } from "../../shared/text/model-special-tokens";

const cases = [
  { in: "Hello<|assistant|>.", out: "Hello." },
  { in: "<|assistant|>Hello", out: "Hello" },
  { in: "Hello<|assistant|>", out: "Hello" },
  { in: "(<|assistant|>Hello)", out: "(Hello)" },
];

it("does not insert spaces around punctuation or at string boundaries when stripping model tokens", () => {
  const outs = cases.map(c => stripModelSpecialTokens(c.in));
  const expected = cases.map(c => c.out);
  expect(outs).toEqual(expected);
});
