import React from 'react';
import { witnessFileAction } from './witnessActions.js';

export function WitnessFileAction({ url, label, policy, assetUrl, description }) {
  const action = witnessFileAction(url, { label, policy });
  if (!action) return null;
  return <a href={assetUrl(action.href)} download={action.download || undefined}
    target={action.download ? undefined : '_blank'} rel={action.download ? undefined : 'noreferrer noopener'}
    title={description}>{action.label}</a>;
}
