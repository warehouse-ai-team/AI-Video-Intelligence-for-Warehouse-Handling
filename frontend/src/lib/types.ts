export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type Behaviour =
  | 'dropping'
  | 'throwing'
  | 'dragging'
  | 'rough_handling'
  | 'improper_stacking'
  | 'unstable_stacking'
  | 'outside_designated_area'
  | 'strap_assisted_handling'
  | 'stepping_on_carton'
  | 'unsafe_loading_sequence';

export type DamageStatus = 'potential_damage_risk';

export interface WarehouseEvent {
  event_id: string;
  video_id: string;
  start_frame: number | null;
  end_frame: number | null;
  start_time: number; // seconds into the video
  end_time: number;
  behaviour: Behaviour;
  confidence: number; // 0–1
  evidence: string | null;
  reason: string;
  damage_status: DamageStatus;
  risk_level: RiskLevel;
  risk_score: number; // 0–100
  risk_explanation: string;
  created_at: string;
}

export interface RiskFactors {
  behaviour: Behaviour;
  duration_seconds: number;
  repeat_frequency: number;
  base_score: number;
  confidence_factor: number;
  duration_factor: number;
  repeat_factor: number;
}

export interface RiskScore {
  event_id: string;
  score: number;
  level: RiskLevel;
  factors: RiskFactors;
}

export interface Summary {
  total_events: number;
  low_risk_events: number;
  medium_risk_events: number;
  high_risk_events: number;
  critical_risk_events: number;
  most_common_behaviour: string | null;
  busiest_risky_video: string | null;
}

export interface FilterState {
  video_id?: string; // replaces the old "bay" filter — she has no bay concept
  risk_level?: RiskLevel;
  behaviour?: Behaviour;
}