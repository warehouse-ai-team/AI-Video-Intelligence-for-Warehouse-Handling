import { WarehouseEvent } from './types';

export const mockEvents: WarehouseEvent[] = [
  {
    event_id: 'EVT_MOCK_001',
    video_id: 'V001',
    start_frame: 210,
    end_frame: 260,
    start_time: 7.0,
    end_time: 8.7,
    behaviour: 'rough_handling',
    confidence: 0.91,
    evidence: null,
    reason: 'Rapid deceleration on impact',
    damage_status: 'potential_damage_risk',
    risk_level: 'HIGH',
    risk_score: 73,
    risk_explanation:
      'Risk score 73/100 is based on rough handling, 91% detection confidence, 1.70 seconds duration. This indicates potential handling risk, not confirmed product damage.',
    created_at: '2026-09-04T09:15:12Z',
  },
  {
    event_id: 'EVT_MOCK_002',
    video_id: 'V002',
    start_frame: 900,
    end_frame: 940,
    start_time: 30.0,
    end_time: 31.3,
    behaviour: 'dropping',
    confidence: 0.87,
    evidence: null,
    reason: 'Sudden downward motion followed by a stop',
    damage_status: 'potential_damage_risk',
    risk_level: 'CRITICAL',
    risk_score: 87,
    risk_explanation:
      'Risk score 87/100 is based on dropping, 87% detection confidence, 1.30 seconds duration. This indicates potential handling risk, not confirmed product damage.',
    created_at: '2026-09-04T09:41:03Z',
  },
];