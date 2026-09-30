import { test, expect } from 'vitest';
import { markdownToSignalText } from '../../signal/format';

test('bold-formatted link labels remain exactly the label and do not include appended parenthetical URLs', () => {
  const md = 'See [**boldlabel**](https://a.example) and [**other**](https://b.example)';
  const res = markdownToSignalText(md);
  const text = res.text;
  const styles = res.styles ?? [];
  const bolds = styles
    .filter((s) => s.style === 'BOLD')
    .map((s) => text.slice(s.start, s.start + s.length));
  const hasUrls = text.includes(' (https://a.example)') && text.includes(' (https://b.example)');
  expect({ hasUrls, bolds }).toEqual({ hasUrls: true, bolds: ['boldlabel', 'other'] });
});
