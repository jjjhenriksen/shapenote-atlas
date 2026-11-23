import React, { memo, useEffect, useMemo, useRef, useState } from 'react';
import { scoreToMusicXml } from './scoreMusicXml.js';
import { ScoreTextAlternative } from './ScoreTextAlternative.jsx';

let runtime;
export function loadNotationRuntime() {
  if (!runtime) runtime = import('opensheetmusicdisplay').then((module) => {
    const Constructor = module.OpenSheetMusicDisplay || module.default?.OpenSheetMusicDisplay;
    if (!Constructor) throw new Error('Notation runtime did not initialize.');
    return Constructor;
  }).catch((error) => { runtime = null; throw error; });
  return runtime;
}

// Each effect owns a separate DOM mount. An obsolete asynchronous load may
// finish, but it can never render into or clear the replacement witness.
export const ScoreEngraving = memo(function ScoreEngraving({ score, sourceKey, targetKey, transpose, reviewDraft, runtimeLoader = loadNotationRuntime }) {
  const host = useRef(null);
  const scrollRegion = useRef(null);
  const retryButton = useRef(null);
  const retryFocusKey = useRef(null);
  const [attempt, setAttempt] = useState(0);
  const [width, setWidth] = useState(0);
  const [state, setState] = useState({ status: 'loading', key: '' });
  const converted = useMemo(() => {
    try { return scoreToMusicXml(score, { sourceKey, targetKey, transpose, reviewDraft }); }
    catch (error) { return { error: error.message }; }
  }, [score, sourceKey, targetKey, transpose, reviewDraft]);
  const renderKey = converted.xml || converted.error;

  useEffect(() => {
    const element = host.current;
    const resize = () => setWidth(Math.max(640, Math.floor(element.parentElement.clientWidth)));
    resize();
    const observer = new ResizeObserver(resize); observer.observe(element.parentElement);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!width) return;
    const element = host.current;
    const mount = document.createElement('div');
    mount.className = 'notation-mount'; mount.style.width = `${width}px`;
    element.replaceChildren(mount);
    let cancelled = false, engine;
    setState({ status: 'loading', key: renderKey });
    (async () => {
      if (converted.error) throw new Error(converted.error);
      const Constructor = await runtimeLoader();
      if (cancelled) return;
      engine = new Constructor(mount, { backend: 'svg', autoResize: false, drawTitle: false, drawComposer: false, drawPartNames: true, drawMeasureNumbers: false, drawLyrics: true, drawingParameters: 'compacttight', pageFormat: 'Endless' });
      engine.EngravingRules.HorizontalBetweenLyricsDistance = 0.5;
      engine.EngravingRules.MaximumLyricsElongationFactor = 6;
      engine.EngravingRules.LyricsXPaddingFactorForLongLyrics = 1.4;
      // Preserve printed shape geometry; use the same MusicXML→OSMD path as
      // Hollow Square, with Atlas lyrics and source semantics enabled.
      await engine.load(converted.xml);
      if (cancelled) return;
      engine.render();
      if (!mount.querySelector('svg')) throw new Error('The source score produced no engraving.');
      mount.querySelectorAll('svg').forEach((svg) => { svg.setAttribute('aria-hidden', 'true'); svg.classList.add('score-svg'); });
      setState({ status: 'ready', key: renderKey });
    })().catch((error) => {
      if (cancelled) return;
      mount.replaceChildren();
      setState({ status: 'error', key: renderKey, message: error.message || 'Notation could not be rendered.' });
    });
    return () => { cancelled = true; engine?.clear(); mount.remove(); };
  }, [converted, renderKey, width, attempt, runtimeLoader]);

  const current = state.key === renderKey ? state : { status: 'loading' };
  useEffect(() => {
    if (retryFocusKey.current !== renderKey) {
      retryFocusKey.current = null;
      return;
    }
    if (current.status === 'loading') return;
    // Retry replaces its focused button while loading. Restore the keyboard
    // position only if the reader has not moved focus elsewhere in the meantime.
    if (document.activeElement === document.body) {
      (current.status === 'ready' ? scrollRegion.current : retryButton.current)?.focus({ preventScroll: true });
    }
    retryFocusKey.current = null;
  }, [current.status, renderKey]);
  return <>
    <div className="notation-status" aria-live="polite">
      {current.status === 'loading' && <p role="status">Engraving the available source score…</p>}
      {current.status === 'error' && <div role="alert"><p>Notation unavailable: {current.message}</p><button ref={retryButton} type="button" onClick={(event) => {
        retryFocusKey.current = document.activeElement === event.currentTarget ? renderKey : null;
        setAttempt((value) => value + 1);
      }}>Retry notation</button></div>}
    </div>
    <div ref={scrollRegion} className="score-scroll" role="region" aria-label="Score notation; scroll horizontally to view all notes" tabIndex={current.status === 'ready' ? 0 : -1} aria-hidden={current.status !== 'ready'} aria-busy={current.status === 'loading'}>
      <div ref={host} className="score-engraving" role="img" aria-label={`Available source score with ${score?.parts?.length || 0} parts; ${converted.measureCount || 0} measures. Source lyrics, ties and repeats are shown only where encoded.`} data-render-state={current.status} data-renderer="osmd" />
    </div>
    <ScoreTextAlternative score={score} sourceKey={sourceKey} targetKey={targetKey} transpose={transpose} reviewDraft={reviewDraft} />
  </>;
});
