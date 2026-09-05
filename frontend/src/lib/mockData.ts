import { WarehouseEvent } from './types';

export const mockEvents: WarehouseEvent[] = [
  {
    event_id: 'evt_001',
    video_id: 'vid_bay3_0904',
    track_id: 'trk_014',
    behaviour_type: 'rough_handling',
    confidence: 0.91,
    timestamp: '2026-09-04T10:35:12Z',
    video_time_seconds: 277,
    bbox: { x: 120, y: 80, width: 60, height: 90 },
    bay: 'Bay 3',
    risk_level: 'high',
    risk_explanation:
      'Rapid deceleration on impact combined with a repeat occurrence for this track ID in the last 5 minutes.',
  },
  {
    event_id: 'evt_002',
    video_id: 'vid_bay1_0904',
    track_id: 'trk_009',
    behaviour_type: 'drop',
    confidence: 0.87,
    timestamp: '2026-09-04T10:41:03Z',
    video_time_seconds: 663,
    bbox: { x: 210, y: 140, width: 45, height: 45 },
    bay: 'Bay 1',
    risk_level: 'critical',
    risk_explanation:
      'Drop height estimated above the safety threshold with no equipment assist detected.',
  },
  {
    event_id: 'evt_003',
    video_id: 'vid_bay2_0904',
    track_id: 'trk_022',
    behaviour_type: 'outside_designated_area',
    confidence: 0.76,
    timestamp: '2026-09-04T11:02:47Z',
    video_time_seconds: 1367,
    bbox: { x: 300, y: 60, width: 50, height: 100 },
    bay: 'Bay 2',
    risk_level: 'medium',
    risk_explanation:
      'Object tracked outside the marked handling zone for over 8 seconds.',
  },
  {
    event_id: 'evt_004',
    video_id: 'vid_bay3_0904',
    track_id: 'trk_014',
    behaviour_type: 'unstable_stacking',
    confidence: 0.68,
    timestamp: '2026-09-04T11:10:30Z',
    video_time_seconds: 1830,
    bbox: { x: 90, y: 50, width: 80, height: 120 },
    bay: 'Bay 3',
    risk_level: 'low',
    risk_explanation:
      'Minor lean detected on stacked pallet, within recoverable tolerance.',
  },
];