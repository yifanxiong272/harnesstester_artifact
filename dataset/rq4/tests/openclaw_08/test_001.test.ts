import { test, expect } from 'vitest';
import { stripFormattedReasoningMessage } from '../../shared/text/formatted-reasoning-message';

test('preserve substantive body leading/trailing whitespace', () => {
  const input =
    'Thinking...' + '\n' +
    '_brief summary_' + '\n' +
    '' + '\n' +
    '  first substantive line  ' + '\n' +
    ' last substantive line ';

  const result = stripFormattedReasoningMessage(input);

  const expected = '  first substantive line  \n last substantive line ';
  expect(result).toBe(expected);
});
