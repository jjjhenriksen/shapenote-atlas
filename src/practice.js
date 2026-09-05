import { playbackEvents } from "./agent_11_score_semantics.js";

export function buildPracticeSchedule(parts, playback, loops = 1) {
  const hasEvidence = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const timingComplete = Boolean(playback?.measureSequence?.length) && playback.measureSequence.every((measure) => hasEvidence(playback.measureStarts?.[String(measure)]) && hasEvidence(playback.measureDurations?.[String(measure)]) && Number(playback.measureDurations[String(measure)]) > 0);
  const expandAllowed = playback?.status === 'encoded' && playback.safeToApply === true && timingComplete;
  const boundedLoops = expandAllowed ? Math.max(1, Math.min(8, Number(loops) || 1)) : 1;
  const expanded = (parts || []).map((part) => {
    const sourceEvents = part.events || [];
    if (!expandAllowed) return { ...part, events: sourceEvents };
    const starts = playback.measureStarts || {}; const durations = playback.measureDurations || {};
    const byMeasure = new Map(); sourceEvents.forEach((event) => { const key = String(event.measure); if (!byMeasure.has(key)) byMeasure.set(key, []); byMeasure.get(key).push(event); });
    let offset = 0; const events = [];
    playback.measureSequence.forEach((measure) => { const key = String(measure); const base = Number(starts[key]); const duration = Number(durations[key]); if (!Number.isFinite(base) || !Number.isFinite(duration) || duration <= 0) return; (byMeasure.get(key) || []).forEach((event) => { events.push({ ...event, onset: offset + Number(event.onset) - base }); }); offset += duration; });
    return { ...part, events };
  });
  const duration = Math.max(...expanded.flatMap((part) => part.events.map((event) => Number(event.onset) + Number(event.beats)).filter(Number.isFinite)), 1);
  const sequenceDuration = expandAllowed ? playback.measureSequence.reduce((sum, measure) => sum + Number(playback.measureDurations[String(measure)]), 0) : duration;
  const totalDuration = sequenceDuration * boundedLoops;
  return { duration: totalDuration, events: Array.from({ length: boundedLoops }, (_, loopIndex) => expanded.flatMap((part) => part.events.map((event) => ({ ...event, partName: part.name, loopIndex, scheduledOnset: Number(event.onset) + loopIndex * sequenceDuration })))).flat() };
}

export function sessionIsCurrent(active, session) {
  return active === session && !session?.cancelled;
}

export function shouldCompleteSession(currentTime, session) {
  return sessionIsCurrent(session.owner, session) && Number(currentTime) - session.startedAt >= session.duration;
}

export function stopScheduledNodes(nodes) {
  (nodes || []).forEach((node) => { try { node.stop(); } catch {} });
}

export async function guardedAudioAction(action, active, session) {
  await action();
  return sessionIsCurrent(active, session);
}

export function resolvePlaybackQuarantine(preview, fullScore) {
  const records = [preview?.playbackValidation, fullScore?.playbackValidation].filter(Boolean);
  const blocked = records.find((record) => record.status === 'quarantined' || record.safeToApply === false);
  return blocked ? { quarantined: true, reason: blocked.reason || blocked.message || 'Playback validation failed.' } : { quarantined: false, reason: '' };
}

export function scheduleWithCleanup(events, createNode, configureNode = () => {}) {
  const nodes = [];
  try {
    for (const event of events || []) {
      const node = createNode(event);
      nodes.push(node);
      configureNode(node, event);
    }
    return nodes;
  } catch (error) {
    stopScheduledNodes(nodes);
    throw error;
  }
}
