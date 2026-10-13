import test from 'node:test';
import assert from 'node:assert/strict';
import { scoreSystemLayout } from '../src/scoreLayout.js';

for (const count of [3, 4, 5]) {
  test(`${count} parts have bounded staves and system separation`, () => {
    const layout = scoreSystemLayout(Array.from({ length: count }, () => ({})));
    const lastBottom = 22 + (count - 1) * layout.staffGap + 16;
    assert.ok(lastBottom < layout.systemHeight - 8);
    assert.equal(layout.systemHeight, 26 + count * layout.staffGap);
  });
}
test('encoded lyric verses reserve additional room without inventing underlay', () => {
  const layout = scoreSystemLayout([{ lyrics: [{ number: '1' }, { number: '2' }] }, {}]);
  assert.equal(layout.staffGap, 71);
  assert.ok(layout.systemHeight > scoreSystemLayout([{}, {}]).systemHeight);
});
