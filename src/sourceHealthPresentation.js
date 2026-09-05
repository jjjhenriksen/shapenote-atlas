const EVIDENCE_STATES = ['current', 'cached', 'offline', 'budget', 'unknown'];
const NETWORK_STATES = ['reachable', 'redirected', 'unreachable', 'network-error', 'not-checked-offline', 'not-checked-budget', 'unknown'];
const RETENTION_STATES = ['retained-exact', 'local-drift', 'retention-unavailable', 'missing-retention', 'unknown-retention'];

export const SOURCE_HEALTH_STATUS = Object.freeze({
  evidenceLabels: Object.freeze({
    current: 'Current check',
    cached: 'Cached check',
    offline: 'Not checked offline',
    budget: 'Not checked (budget)',
    unknown: 'Evidence state unavailable',
  }),
  networkLabels: Object.freeze({
    reachable: 'Reachable',
    redirected: 'Redirected',
    unreachable: 'Unreachable',
    'network-error': 'Network error',
    'not-checked-offline': 'Not checked offline',
    'not-checked-budget': 'Budget excluded',
    unknown: 'Network state unavailable',
  }),
  retentionLabels: Object.freeze({
    'retained-exact': 'Retained exact evidence (not source authority)',
    'local-drift': 'Retention drift present',
    'retention-unavailable': 'Retention unavailable',
    'missing-retention': 'Retention not recorded',
    'unknown-retention': 'Retention state unavailable',
  }),
});

const hasValue = (value) => typeof value === 'string' && value.length > 0;

function evidenceStateFor(record) {
  if (record?.evidenceAge === 'current') return 'current';
  if (record?.evidenceAge === 'cached') return 'cached';
  if (record?.status === 'cached') return 'cached';
  if (record?.status === 'not-checked-budget' || record?.status === 'budget') return 'budget';
  if (record?.status === 'not-checked-offline') return 'offline';
  if (record?.evidenceAge === 'not-checked') {
    if (record?.status === 'not-checked-budget' || record?.status === 'budget') return 'budget';
    if (record?.status === 'not-checked-offline') return 'offline';
    return 'unknown';
  }
  if (record?.status === 'current' || NETWORK_STATES.includes(record?.status)) return 'current';
  return 'unknown';
}

function networkStateFor(record, evidenceState) {
  const candidate = evidenceState === 'cached'
    ? (record?.networkStatus || record?.cachedStatus)
    : record?.networkStatus || record?.status;
  if (NETWORK_STATES.includes(candidate)) return candidate;
  if (evidenceState === 'budget') return 'not-checked-budget';
  if (evidenceState === 'offline') return 'not-checked-offline';
  return 'unknown';
}

function retentionStateFor(record) {
  const candidate = record?.retentionStatus;
  return RETENTION_STATES.includes(candidate) ? candidate : 'unknown-retention';
}

function networkCheckedAtFor(record) {
  // checkedAt is only the report timestamp. It is intentionally not a
  // fallback: it does not prove that a network request happened then.
  return hasValue(record?.networkCheckedAt) ? record.networkCheckedAt : null;
}

export function formatSourceHealthDate(timestamp) {
  return hasValue(timestamp) ? timestamp.slice(0, 10) : 'date unavailable';
}

export function presentSourceHealthRecord(record = {}) {
  const evidenceState = evidenceStateFor(record);
  const networkState = networkStateFor(record, evidenceState);
  const retentionState = retentionStateFor(record);
  const networkCheckedAt = networkCheckedAtFor(record);
  const evidenceLabel = SOURCE_HEALTH_STATUS.evidenceLabels[evidenceState];
  const networkLabel = SOURCE_HEALTH_STATUS.networkLabels[networkState];
  const retentionLabel = SOURCE_HEALTH_STATUS.retentionLabels[retentionState];
  return {
    evidenceState,
    evidenceLabel,
    networkState,
    networkLabel,
    retentionState,
    retentionLabel,
    networkCheckedAt,
    networkCheckedDate: formatSourceHealthDate(networkCheckedAt),
    sourceAuthority: 'not-established',
    text: `${evidenceLabel} · ${networkLabel} · ${retentionLabel} · last network check ${formatSourceHealthDate(networkCheckedAt)}`,
  };
}

function countsFor(values, keys) {
  return Object.fromEntries(keys.map((key) => [key, values.filter((value) => value === key).length]));
}

function retentionSummary(states) {
  if (states.includes('local-drift')) {
    return { state: 'local-drift', label: 'Mixed retention evidence; drift present' };
  }
  if (states.includes('retained-exact') && (states.includes('retention-unavailable') || states.includes('missing-retention') || states.includes('unknown-retention'))) {
    return { state: 'mixed-retention', label: states.includes('unknown-retention') ? 'Mixed retention evidence; some retention state is unavailable' : 'Mixed retention evidence; exact retention is not universal' };
  }
  if (states.includes('retained-exact')) {
    return { state: 'retained-exact', label: SOURCE_HEALTH_STATUS.retentionLabels['retained-exact'] };
  }
  if (states.includes('retention-unavailable')) {
    return { state: 'retention-unavailable', label: SOURCE_HEALTH_STATUS.retentionLabels['retention-unavailable'] };
  }
  if (states.includes('missing-retention')) {
    return { state: 'missing-retention', label: SOURCE_HEALTH_STATUS.retentionLabels['missing-retention'] };
  }
  return { state: 'unknown-retention', label: SOURCE_HEALTH_STATUS.retentionLabels['unknown-retention'] };
}

export function summarizeSourceHealth(records = []) {
  const presented = records.filter(Boolean).map(presentSourceHealthRecord);
  const evidenceStates = presented.map((item) => item.evidenceState);
  const networkStates = presented.map((item) => item.networkState);
  const retentionStates = presented.map((item) => item.retentionState);
  const latestNetworkCheckedAt = presented.map((item) => item.networkCheckedAt).filter(Boolean).sort().at(-1) || null;
  const evidenceCounts = countsFor(evidenceStates, EVIDENCE_STATES);
  const networkCounts = countsFor(networkStates, NETWORK_STATES);
  const retentionCounts = countsFor(retentionStates, RETENTION_STATES);
  const evidenceText = `${evidenceCounts.current} current · ${evidenceCounts.cached} cached · ${evidenceCounts.budget} budget-excluded · ${evidenceCounts.offline} offline-unchecked · ${evidenceCounts.unknown} evidence-state-unavailable`;
  const networkText = `${networkCounts.reachable} reachable · ${networkCounts.redirected} redirected · ${networkCounts.unreachable} unreachable · ${networkCounts['network-error']} network error${networkCounts['network-error'] === 1 ? '' : 's'}`;
  const retention = retentionSummary(retentionStates);
  return {
    total: presented.length,
    evidenceCounts,
    networkCounts,
    retentionCounts,
    retentionState: retention.state,
    retentionLabel: retention.label,
    latestNetworkCheckedAt,
    latestNetworkCheckedDate: formatSourceHealthDate(latestNetworkCheckedAt),
    sourceAuthority: 'not-established',
    text: `${evidenceText} · ${networkText} · last network check ${formatSourceHealthDate(latestNetworkCheckedAt)}`,
  };
}

export { EVIDENCE_STATES, NETWORK_STATES, RETENTION_STATES };
