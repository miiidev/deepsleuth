import axios from "axios";

const client = axios.create({
  baseURL: "/api/v1",
});

export interface FaceData {
  bbox: number[];
  score: number;
  heatmap: number[];
}

export interface FrameFaceData {
  frame: number;
  faces: FaceData[];
}

export interface SpatialSignal {
  score: number;
  regions: Record<string, number>;
  explanation: string;
}

export interface TemporalSignal {
  score: number;
  blink_score: number;
  pose_score: number;
  blink_count: number;
  blinks_per_min: number;
  yaw_var: number;
  pitch_var: number;
  roll_var: number;
  explanation: string;
}

export interface FrequencySignal {
  score: number;
  explanation: string;
}

export interface AnalysisResult {
  fused_score: number;
  spatial_score: number;
  frequency_score: number;
  temporal_score: number;
  suspicion_level: string;
  summary: string;
  signals: {
    spatial: SpatialSignal;
    temporal: TemporalSignal;
    frequency: FrequencySignal;
  };
}

export interface TaskStatus {
  task_id: string;
  status: string;
  progress: number;
  message: string;
  error: string | null;
  frame_scores: number[];
  frame_face_data: FrameFaceData[];
  analysis_result: AnalysisResult | null;
  created_at: string;
  updated_at: string;
}

export interface UploadResponse {
  task_id: string;
}

export async function uploadVideo(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await client.post<UploadResponse>("/upload", form);
  return res.data;
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const res = await client.get<TaskStatus>(`/task/${taskId}`);
  return res.data;
}

export function getVideoUrl(taskId: string): string {
  return `/api/v1/result/${taskId}/video`;
}

export function getOriginalVideoUrl(taskId: string): string {
  return `/api/v1/result/${taskId}/original`;
}

export function getReportUrl(taskId: string): string {
  return `/api/v1/result/${taskId}/report`;
}
