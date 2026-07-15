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
  blink_count: number;
  blinks_per_min: number;
  flickering_score: number;
  landmark_stability: number;
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

export interface HistoryEntry {
  id: string;
  filename: string;
  suspicion_level: string;
  fused_score: number;
  created_at: string;
}

export interface HistoryListResponse {
  items: HistoryEntry[];
  total: number;
  page: number;
  per_page: number;
}

export async function getHistory(page: number = 1, perPage: number = 20): Promise<HistoryListResponse> {
  const res = await client.get<HistoryListResponse>("/history", {
    params: { page, per_page: perPage },
  });
  return res.data;
}

export async function deleteHistory(taskId: string): Promise<void> {
  await client.delete(`/history/${taskId}`);
}

export interface HistoryDetail {
  task_id: string;
  filename: string;
  status: string;
  progress: number;
  message: string;
  video_path: string | null;
  result_report_path: string | null;
  error: string | null;
  frame_scores: number[];
  frame_face_data: FrameFaceData[];
  analysis_result: AnalysisResult | null;
  created_at: string;
  updated_at: string;
}

export async function getHistoryDetail(taskId: string): Promise<HistoryDetail> {
  const res = await client.get<HistoryDetail>(`/history/${taskId}`);
  return res.data;
}

export interface BenchmarkMetrics {
  version: string;
  benchmark: {
    dataset: string;
    quality: string;
    test_samples: number;
    accuracy: number;
    f1: number;
    precision: number;
    recall: number;
    split_ratio: string;
    model: string;
    epochs: number;
  };
}

export async function getMetrics(): Promise<BenchmarkMetrics> {
  const res = await client.get<BenchmarkMetrics>("/metrics");
  return res.data;
}


