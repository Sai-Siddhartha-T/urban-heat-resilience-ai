import { request, RequestOptions } from "./services/apiClient";
import { reportService } from "./services/reportService";
import { fmt as fmtUtil, label as labelUtil } from "./lib/utils";

export async function api<T = any>(
  path: string,
  body?: unknown,
  options?: RequestOptions | AbortSignal,
): Promise<T> {
  return request<T>(path, body, options);
}

export async function download(url: string, name: string): Promise<void> {
  return reportService.downloadFile(url, name);
}

export const fmt = fmtUtil;
export const label = labelUtil;

export { type RequestOptions };
export * from "./services";
