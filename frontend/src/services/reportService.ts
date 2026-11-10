import { request } from "./apiClient";
import type { City, ReportGenerateResponse } from "../types";

export const reportService = {
  generateReport(city: City | string): Promise<ReportGenerateResponse> {
    return request<ReportGenerateResponse>("/api/reports/generate", { city });
  },

  async downloadFile(url: string, filename: string): Promise<void> {
    const token = typeof sessionStorage !== "undefined" ? sessionStorage.getItem("heatwise-token") : null;
    const response = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) {
      throw new Error(`Download failed with status ${response.status}`);
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  },
};
