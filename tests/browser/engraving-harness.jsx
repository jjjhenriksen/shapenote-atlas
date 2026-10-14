// Browser-only dependency injection: exercise the real component/runtime while
// controlling async delivery and one constructor failure, without production globals.
import React from 'react';
import { createRoot } from 'react-dom/client';
import { ScoreEngraving, loadNotationRuntime } from '../../src/ScoreEngraving.jsx';
export async function mountHarness(element, score, options = {}) {
  const Constructor = await loadNotationRuntime();
  const trace = { attempts: 0, renders: [], release: null };
  class Observed extends Constructor {
    async load(xml) {
      this.testTitle = new DOMParser().parseFromString(xml, 'text/xml').querySelector('work-title')?.textContent;
      await super.load(xml);
      if (this.testTitle === 'Slow witness') await new Promise((resolve) => { trace.release = resolve; });
    }
    render() { trace.renders.push(this.testTitle); return super.render(); }
  }
  const loader = async () => {
    trace.attempts++;
    if (options.failOnce && trace.attempts === 1) throw new Error('Simulated runtime delivery failure');
    return Observed;
  };
  const root = createRoot(element);
  const show = (next) => root.render(<ScoreEngraving score={next} sourceKey={next.keySignature} transpose={0} runtimeLoader={loader} />);
  show(score);
  return { trace, show, unmount: () => root.unmount() };
}
