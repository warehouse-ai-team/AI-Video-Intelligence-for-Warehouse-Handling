// Shared contract with Behaviour Intelligence / Risk Engine / Backend.
// Do NOT invent fields that aren't in this schema — the AI assistant
// must only ever reason about fields defined here.

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export type BehaviourType =
  | 'drop'
  | 'drag'
  | 'rough_handling'
  | 'unstable_stacking'
  | 'outside_designated_area'
  | 'no_equipment_used'
  | 'incorrect_pallet_placement'
  | 'push_or_throw'
  | 'unsafe_sequence'
  | 'overloading';

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface WarehouseEvent {
  event_id: string;
  video_id: string;
  track_id: string;
  behaviour_type: BehaviourType;
  confidence: number; // 0–1
  timestamp: string; // ISO 8601
  video_time_seconds: number; // offset into the source video, for replay
  bbox: BoundingBox;
  bay?: string;
  risk_level: RiskLevel;
  risk_explanation?: string; // human-readable reasoning from the risk engine
}

export interface RiskScore {
  event_id: string;
  score: number; // numeric risk score, engine-defined range
  level: RiskLevel;
  factors: {
    behaviour_type: BehaviourType;
    duration_seconds?: number;
    repeat_frequency?: number;
    impact_proxy?: number;
  };
}

export interface FilterState {
  dateRange?: { from: string; to: string };
  bay?: string;
  riskLevel?: RiskLevel;
  behaviourType?: BehaviourType;
}