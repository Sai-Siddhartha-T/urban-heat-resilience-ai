import { request } from "./apiClient";
import type { ChatRequest, ChatResponse } from "../types";

export const aiService = {
  chat(req: ChatRequest): Promise<ChatResponse> {
    return request<ChatResponse>("/api/ai/chat", req);
  },
};
