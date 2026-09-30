import { it, expect } from "vitest";
import { parseMentions } from "../../../extensions/msteams/src/mentions";

it("accepts Bot Framework IDs with arbitrary non-empty suffix after '28:' and replaces token with <at>Name</at>", () => {
  const originalId = "28:az09-Zz";
  const input = `Hello @[Bot User](${originalId})!`;

  const result = parseMentions(input);

  expect(result).toEqual({
    text: "Hello <at>Bot User</at>!",
    entities: [
      {
        type: "mention",
        text: "<at>Bot User</at>",
        mentioned: {
          id: originalId,
          name: "Bot User",
        },
      },
    ],
  });
});
